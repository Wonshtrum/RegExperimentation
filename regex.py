from time import time


NOT_MATCH = False
HAS_MATCH = True
EPSILON = None



class Regex:
	def advance(self):
		return []
	def reset(self):
		pass
	def copy(self):
		return self


class CharSet:
	min_char = 0
	max_char = 127
	def __new__(cls, *ranges, **kwargs):
		if not ranges and EPSILON is not None:
			return EPSILON
		return object.__new__(cls)

	def __init__(self, *ranges, inverted=False):
		ranges = sorted((_, _) if isinstance(_, int) else _ for _ in ranges)
		self.ranges = []
		last = CharSet.min_char-1
		for min_char, max_char in ranges:
			if min_char <= last:
				min_char, old_max_char = self.ranges.pop()
				max_char = max(max_char, old_max_char)
			self.ranges.append((min_char, max_char))
			last = max_char+1

		if inverted:
			self.ranges = self.star.intersect(self)[0].ranges

	def contains(self, char):
		return any(min_char <= char <= max_char for min_char, max_char in self.ranges)

	def union(self, other):
		return CharSet(*self.ranges, *other.ranges)

	def intersect(self, other):
		in_self = []
		in_both = []
		in_other = []
		i = 0
		j = 0
		get = lambda l, i: l[i] if i < len(l) else (CharSet.max_char+1, CharSet.max_char+1)
		self_min, self_max = get(self.ranges, i)
		other_min, other_max = get(other.ranges, j)
		while i < len(self.ranges) or j < len(other.ranges):
			if self_max < other_min:
				i += 1
				in_self.append((self_min, self_max))
				self_min, self_max = get(self.ranges, i)
				continue
			if other_max < self_min:
				j += 1
				in_other.append((other_min, other_max))
				other_min, other_max = get(other.ranges, j)
				continue

			if self_min < other_min:
				in_self.append((self_min, other_min-1))
				self_min = other_min
			if other_min < self_min:
				in_other.append((other_min, self_min-1))
				other_min = self_min

			if self_max < other_max:
				i += 1
				in_both.append((self_min, self_max))
				other_min = self_max+1
				self_min, self_max = get(self.ranges, i)
			elif other_max < self_max:
				j += 1
				in_both.append((other_min, other_max))
				self_min = other_max+1
				other_min, other_max = get(other.ranges, j)
			else:
				i += 1
				j += 1
				in_both.append((self_min, self_max))
				self_min, self_max = get(self.ranges, i)
				other_min, other_max = get(other.ranges, j)
		return CharSet(*in_self), CharSet(*in_other), CharSet(*in_both)

	def get_one(self):
		if len(self.ranges) == 0:
			return ""
		return chr(self.ranges[0][0])

	def __hash__(self):
		return hash(tuple(self.ranges))

	def __eq__(self, other):
		return self.ranges == other.ranges

	def __repr__(self):
		if len(self.ranges) == 0:
			return "ε"
		if len(self.ranges) == 1 and self.ranges[0][0] == self.ranges[0][1]:
			return f"{chr(self.ranges[0][0])}"
		return "["+"".join(f"{chr(min_char)}" if min_char==max_char else f"{chr(min_char)}-{chr(max_char)}" for min_char, max_char in self.ranges)+"]"


CharSet.star = CharSet((CharSet.min_char, CharSet.max_char))
EPSILON = CharSet()


def to_string(entry):
	return "".join(_.get_one() if isinstance(_, CharSet) else chr(_) for _ in entry)


def to_ascii(entry):
	return list(map(ord, entry))


class Atom(Regex):
	def __init__(self, *ranges, inverted=False, consumed=False):
		self.char_set = CharSet(*ranges, inverted=inverted)
		self.consumed = consumed

	def advance(self):
		copy = self.copy()
		if self.consumed:
			return [(EPSILON, HAS_MATCH, copy)]
		copy.consumed = True
		return [(self.char_set, HAS_MATCH, copy)]

	def reset(self):
		self.consumed = False

	def copy(self):
		return Atom(*self.char_set.ranges, consumed=self.consumed)

	def __eq__(self, other):
		return self.consumed == other.consumed

	def __repr__(self):
		return f"{self.char_set}"


class Repeat(Regex):
	NO_MAX = ""
	def __init__(self, expr, min=0, max=NO_MAX, count=0):
		self.expr = expr
		self.min = min
		self.max = max
		self.count = count
		self.dirty = False

	def advance(self):
		result = []
		if not self.dirty and self.count >= self.min:
			result.append((EPSILON, HAS_MATCH, self.copy()))
		if self.count == self.max:
			return result
		sub_exprs = self.expr.advance()
		for path, status, sub_expr in sub_exprs:
			copy = self.copy()
			copy.expr = sub_expr
			if status == HAS_MATCH:
				copy.expr.reset()
				copy.count += 1
				if copy.count == self.max:
					result.append((path, HAS_MATCH, copy))
					continue
				if path is EPSILON:
					result.extend(copy.advance())
					continue
				if copy.count >= self.min:
					result.append((path, HAS_MATCH, copy.copy()))
			copy.dirty = True
			result.append((path, NOT_MATCH, copy))
		return result

	def reset(self):
		self.count = 0
		self.dirty = False
		self.expr.reset()

	def copy(self):
		return Repeat(self.expr, min=self.min, max=self.max, count=self.count)

	def __eq__(self, other):
		return (self.count == other.count or (self.count >= self.min and other.count >= other.min and self.max == Repeat.NO_MAX)) and self.expr == other.expr

	def __repr__(self):
		return f"{self.expr}{{{self.min},{self.count},{self.max}}}"


class Choice(Regex):
	def __init__(self, *exprs, cursor=None):
		self.exprs = list(exprs)
		self.cursor = cursor

	def advance(self):
		result = []
		if self.cursor is None:
			copy = self.copy()
			for i, expr in enumerate(self.exprs):
				copy.cursor = i
				result.extend(copy.advance())
			return result
		sub_exprs = self.exprs[self.cursor].advance()
		for path, status, sub_expr in sub_exprs:
			copy = self.copy()
			copy.exprs[self.cursor] = sub_expr
			result.append((path, status, copy))
		return result

	def reset(self):
		self.cursor = None
		for expr in self.exprs:
			expr.reset()

	def copy(self):
		return Choice(*self.exprs, cursor=self.cursor)

	def __eq__(self, other):
		return self.cursor == other.cursor and (self.cursor is None or self.exprs[self.cursor] == other.exprs[other.cursor])

	def __repr__(self):
		return "("+"|".join(
			f" >{expr}< " if i == self.cursor else
			f"{expr}" for i, expr in enumerate(self.exprs)
		)+")"


class Sequence(Regex):
	def __init__(self, *exprs, cursor=0):
		self.exprs = list(exprs)
		self.cursor = cursor

	def advance(self):
		result = []
		if self.cursor == len(self.exprs):
			result.append((EPSILON, HAS_MATCH, self))
			return result
		sub_exprs = self.exprs[self.cursor].advance()
		for path, status, sub_expr in sub_exprs:
			copy = self.copy()
			copy.exprs[self.cursor] = sub_expr
			if status == HAS_MATCH:
				copy.cursor += 1
			if copy.cursor == len(self.exprs):
				result.append((path, HAS_MATCH, copy))
				continue
			if path is EPSILON:
				result.extend(copy.advance())
				continue
			result.append((path, NOT_MATCH, copy))
		return result

	def reset(self):
		self.cursor = 0
		for expr in self.exprs:
			expr.reset()

	def copy(self):
		return Sequence(*self.exprs, cursor=self.cursor)

	def __eq__(self, other):
		return self.cursor == other.cursor and (self.cursor == len(self.exprs) or self.exprs[self.cursor] == other.exprs[other.cursor])

	def __repr__(self):
		return "("+"".join(
			f" >{expr}< " if i == self.cursor else
			f"{expr}" for i, expr in enumerate(self.exprs)
		)+")"


class Family(Regex):
	def __init__(self, expr, id):
		self.id = id
		self.expr = expr

	def advance(self):
		result = []
		sub_exprs = self.expr.advance()
		for path, status, sub_expr in sub_exprs:
			copy = self.copy()
			copy.expr = sub_expr
			result.append((path, status, copy))
		return result

	def reset(self):
		self.expr.reset()

	def copy(self):
		return Family(self.expr, self.id)

	def __eq__(self, other):
		return isinstance(other, Family) and self.id == other.id and self.expr == other.expr

	def __repr__(self):
		return f"{self.expr}->{self.id}"


def add_unique(state, expr):
	if all(expr != other for other in state):
		state.append(expr)
		return state, True
	return state, False


def unify(transitions):
	unified = {}
	visited = []
	change = False
	for path, state in transitions.items():
		if state in visited:
			change = True
			continue
		visited.append(state)
		for other_path, other_state in transitions.items():
			if state == other_state:
				path = path.union(other_path)
		unified[path] = state
	transitions.clear()
	transitions.update(unified)
	return change


class RegexMatch:
	def __init__(self, entry, length, families):
		self.entry = entry
		self.length = length
		self.families = families

	def __repr__(self):
		return f" {to_string(self.entry)}\n{' '*(self.length>0)}{'~'*(self.length-1)}^\n"+"".join(map(str, self.families))


class RegexGraph(list):
	def __init__(self, *exprs):
		super().__init__([[{}, [], [Family(expr, i) for i, expr in enumerate(exprs)]]])

	i = -1
	def match(self, entry, state_id=0, shortest=False):
		state = self[state_id]
		current = None
		i = 0
		for i, char in enumerate(entry):
			if state[1]:
				print("there")
				current = RegexMatch(entry, i, state[1])
				if shortest:
					return current
			for path, state_id in state[0].items():
				if path.contains(char):
					state = self[state_id]
					break
			else:
				return current
		else:
			if state[1]:
				print("here")
				return RegexMatch(entry, i+1, state[1])
			return current
		
	def run(self, entry, state_id=0):
		state = self[state_id]
		for i, char in enumerate(entry):
			for path, state_id in state[0].items():
				if path.contains(char):
					state = self[state_id]
					break
			else:
				print("No match:", to_string(entry))
				print("          "+" "*i+"^")
				break
		else:
			if state[1]:
				print("Matches:")
				for expr in state[1]:
					print("", expr)
			else:
				print("No match:", to_string(entry))

	def run_back(self, state_id, result=None, visited=None):
		if visited is None:
			visited = []
		if result is None:
			result = []
		if state_id == 0:
			return result[::-1]
		state = self[state_id]
		visited += [state_id]
		for i, (transitions, _, _) in enumerate(self):
			if i in visited:
				continue
			for path, j in transitions.items():
				if j == state_id:
					found = self.run_back(i, result+[path], visited)
					if found:
						return found
		else:
			return False

	def _compile(self, state_id=0):
		stop = len(self)
		for i in range(state_id, stop):
			transitions, accept, exprs = self[i]
			for j, expr in enumerate(exprs):
				sub_exprs = expr.advance()
				for path, status, sub_expr in sub_exprs:
					if path is EPSILON:
						add_unique(accept, expr)
						continue
					for other_path, other_state in list(transitions.items()):
						path, in_other, in_both = path.intersect(other_path)
						del transitions[other_path]
						if in_other is not EPSILON:
							transitions[in_other] = other_state
						if in_both is not EPSILON:
							both_state, _ = add_unique(list(other_state), sub_expr)
							transitions[in_both] = both_state
						if path is EPSILON:
							break
					else:
						transitions[path] = [sub_expr]
			for path, state in transitions.items():
				for i, (_, accept, other_state) in enumerate(self):
					if (all(any(expr == other for other in other_state) for expr in state) and
						all(any(expr == other for expr in state) for other in other_state)):
						transitions[path] = i
						break
				else:
					transitions[path] = len(self)
					self.append([{}, [], state])
			unify(transitions)
		return stop

	def compile(self, max_state=None):
		last = None
		state = 0
		t = time()
		while state != last and (max_state is None or state < max_state):
			last = state
			state = self._compile(last)
		t = time()-t
		print(t)
		return self

	def merge_state(self, i, j, replace=False):
		if replace:
			self[i] = self[j]
		for transitions, _, _ in self:
			for path, k in transitions.items():
				if j == k:
					transitions[path] = i

	def aggregate(self):
		for transitions, accept, _ in self:
			_.clear()
			for i, expr in reversed(list(enumerate(accept))):
				expr.reset()
				if any(expr.id == other.id for other in accept[i+1:]):
					del accept[i]
		change = True
		while change:
			change = False
			for i, (transitions, accept, _) in reversed(list(enumerate(self))):
				change = unify(transitions) or change
				for j, (other_transitions, other_accept, _) in enumerate(self[i+1:]):
					j += i+1
					if (all(any(expr.id == other.id for other in other_accept) for expr in accept) and
						all(any(expr.id == other.id for expr in accept) for other in other_accept) and
						all(other_transitions.get(path) == state for path, state in transitions.items()) and
						all(transitions.get(path) == state for path, state in other_transitions.items())):
						change = True
						self.merge_state(i, j)
						if j < len(self)-1:
							self.merge_state(j, len(self)-1, replace=True)
						del self[j]
						break

	def analyse(self):
		for i, (_, accept, _) in enumerate(self):
			if len(accept) > 1:
				print("Ambiguous expressions:")
				for expr in accept:
					print("-", expr)
				print("can all be matched by:", to_string(self.run_back(i)))
				print()

	def __repr__(self):
		result = ""
		for i, (transitions, accept, state) in enumerate(self):
			result += f"State {i}\n"+"".join(f" {expr}\n" for expr in state)
			result += "accept:\n"+"".join(f" {expr}\n" for expr in accept)
			result += "transitions:\n"+"".join(f" {path} -> {new_state}\n" for path, new_state in transitions.items())
			result += "\n"
		return result

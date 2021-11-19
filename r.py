from time import time


NOT_MATCH = False
HAS_MATCH = True
EPSILON = None


def append(elements, element):
	elements.append(element)
	return elements


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
			self.ranges = self.star.intersect(self)[0]

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

	def __repr__(self):
		if len(self.ranges) == 1 and self.ranges[0][0] == self.ranges[0][1]:
			return f'{self.ranges[0][0]}'
		return '['+','.join(f'{min_char}' if min_char==max_char else f'{min_char}-{max_char}' for min_char, max_char in self.ranges)+']'

CharSet.star = CharSet((CharSet.min_char, CharSet.max_char))
EPSILON = CharSet()


class Atom(Regex):
	def __init__(self, *ranges, consumed=False):
		self.char_set = CharSet(*ranges)
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
		return f'{self.char_set}'


NO_MAX = ""
class Repeat(Regex):
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
		return (self.count == other.count or (self.count >= self.min and other.count >= other.min and self.max == NO_MAX)) and self.expr == other.expr

	def __repr__(self):
		return f'{self.expr}{{{self.min},{self.count},{self.max}}}'


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
		return '('+'|'.join(
			f' {expr} ' if i == self.cursor else
			f'{expr}' for i, expr in enumerate(self.exprs)
		)+')'


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
		return '('+''.join(
			f' {expr} ' if i == self.cursor else
			f'{expr}' for i, expr in enumerate(self.exprs)
		)+')'


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
		return f'{self.expr}->{self.id}'


def merge(graph, i, j, replace=False):
	if replace:
		graph[j] = graph[i]
	graph[i] = []
	for exprs in graph:
		for expr, transition, *_ in exprs:
			for key, val in transition.items():
				if val == i:
					transition[key] = j

def add_unique(state, expr):
	if all(expr != other for other in state):
		state.append(expr)
		return state, True
	return state, False

def _compile(graph, state_id=0):
	stop = len(graph)
	for i in range(state_id, stop):
		transitions, accept, exprs = graph[i]
		for j, expr in enumerate(exprs):
			sub_exprs = expr.advance()
			for path, status, sub_expr in sub_exprs:
				if path is EPSILON:
					add_unique(accept, expr)
					continue
				for other_path in list(transitions.keys()):
					other_state = transitions[other_path]
					path, in_other, in_both = path.intersect(other_path)
					if in_other is not EPSILON:
						transitions[in_other] = other_state
					del transitions[other_path]
					if in_both is not EPSILON:
						both_state, _ = add_unique(list(other_state), sub_expr)
						transitions[in_both] = both_state
					if path is EPSILON:
						break
				else:
					transitions[path] = [sub_expr]

		for path, state in transitions.items():
			for i, (_, accept, other_state) in enumerate(graph):
				if (all(any(expr == other for other in other_state) for expr in state) and
					all(any(expr == other for expr in state) for other in other_state)):
					transitions[path] = i
					break
			else:
				transitions[path] = len(graph)
				graph.append([{}, [], state])

		unified = {}
		visited = []
		for path, state in transitions.items():
			if state in visited:
				continue
			visited.append(state)
			for other_path, other_state in transitions.items():
				if state == other_state:
					path = path.union(other_path)
			unified[path] = state
		transitions.clear()
		transitions.update(unified)

	return stop


def compile(graph, max_state=None):
	last = None
	state = 0
	t = time()
	while state != last and (max_state is None or state < max_state):
		last = state
		state = _compile(graph, last)
	t = time()-t
	print_graph(graph)
	print(t)
	return graph


def print_graph(graph):
	for i, (transitions, accept, state) in enumerate(graph):
		print("State", i)
		for expr in state:
			print("", expr)
		print("accept:")
		for expr in accept:
			print("", expr)
		print("transitions:")
		for path, new_state in transitions.items():
			print("", path, "->", new_state)
		print()


def print_string(string):
	return "".join(map(str, string))


def make_graph(*exprs):
	return [[{}, [], [Family(expr, i) for i, expr in enumerate(exprs)]]]


def run(graph, entry, state_id=0):
	state = graph[state_id]
	for i, char in enumerate(entry):
		for path, state_id in state[0].items():
			if path.contains(char):
				state = graph[state_id]
				break
		else:
			print("No match:", print_string(entry))
			print("          "+" "*i+"^")
			break
	else:
		if state[1]:
			print("Matches:")
			for expr in state[1]:
				print("", expr)
		else:
			print("No match:", print_string(entry))


def run_back(graph, state_id, result=None, visited=None):
	if visited is None:
		visited = []
	if result is None:
		result = []
	if state_id == 0:
		return result[::-1]
	state = graph[state_id]
	visited += [state_id]
	for i, (transitions, _, _) in enumerate(graph):
		if i in visited:
			continue
		for path, j in transitions.items():
			if j == state_id:
				found = run_back(graph, i, result+[path], visited)
				if found:
					return found
	else:
		return False


def analyse(graph):
	for i, (_, accept, _) in enumerate(graph):
		if len(accept) > 1:
			print("Ambiguous expressions:")
			for expr in accept:
				print("-", expr)
			print("can all be matched by:", print_string(run_back(graph, i)))
			print()


a = Atom(1)
b = Atom(2)
n = 30
m = Repeat(a,3)
m = Repeat(Choice(a,b),0)
m = Repeat(Sequence(a,Repeat(b,0,0)),0)
#m = Sequence(Repeat(Sequence(a,b),1),a,b)
#m = Sequence(b,Repeat(Repeat(a,0,1),2,2),b)
#m = Sequence(*[Repeat(a,0,1)]*n, *[a]*n)

graph = make_graph(
	Repeat(a,1),
	Sequence(a,b),
	Repeat(Choice(a,b),1))

graph = make_graph(m)

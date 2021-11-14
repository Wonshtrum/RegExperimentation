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


class Range:
	def __init__(self, char_min, char_max=None):
		self.char_min = char_min
		self.char_max = char_min if char_max is None else char_max

	def __repr__(self):
		if self.char_min == self.char_max:
			return f'"[{self.char_min}]"'
		return f'"[{self.char_min}-{self.char_max}]"'


class Ranges:
	min_char = 0
	max_char = 127
	def __init__(self, *ranges, inverted=False):
		ranges = sorted((_, _) if isinstance(_, int) else _ for _ in ranges)
		self.ranges = []
		last = Ranges.min_char-1
		for min_char, max_char in ranges:
			if min_char <= last:
				min_char, old_max_char = self.ranges.pop()
				max_char = max(max_char, old_max_char)
			self.ranges.append((min_char, max_char))
			last = max_char+1

		if inverted:
			self.ranges = self.star.intersect(self)[0]

	def intersect(self, other):
		in_self = []
		in_both = []
		in_other = []
		i = 0
		j = 0
		get = lambda l, i: l[i] if i < len(l) else (Ranges.max_char+1, Ranges.max_char+1)
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
		return in_self, in_other, in_both

	def __repr__(self):
		return '['+','.join(f'{min_char}' if min_char==max_char else f'{min_char}-{max_char}' for min_char, max_char in self.ranges)+']'

Ranges.star = Ranges((Ranges.min_char, Ranges.max_char))


class Atom(Regex):
	def __init__(self, char):
		self.char = char

	def advance(self):
		return [(Range(self.char), HAS_MATCH, self)]

	def __eq__(self, other):
		return True

	def __repr__(self):
		return f'{self.char}'


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
		if not self.dirty and self.count == self.min == 0:
			result.append((EPSILON, HAS_MATCH, self.copy()))
		sub_exprs = self.expr.advance()
		for path, status, sub_expr in sub_exprs:
			copy = self.copy()
			copy.dirty = True
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
				elif copy.count >= self.min:
					result.append((path, HAS_MATCH, copy.copy()))
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
			f'[{expr}]' if i == self.cursor else
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
			f'[{expr}]' if i == self.cursor else
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


def _compile(graph, state=0):
	stop = len(graph)
	for i in range(state, stop):
		exprs = graph[i]
		transitions = {}
		for j, (expr, transition, *_) in enumerate(exprs):
			sub_exprs = expr.advance()
			for path, status, sub_expr in sub_exprs:
				if path is EPSILON:
					transition[path] = -1
					continue
				path = path.char_min
				if path in transitions:
					state = transitions[path]
					line = graph[state]
				else:
					state = len(graph)
					line = []
					graph.append(line)
				if all(sub_expr != other for other, *_ in line):
					if status == HAS_MATCH:
						line.append([sub_expr, {EPSILON:-1}])
					else:
						line.append([sub_expr, {}])
				transition[path] = transitions[path] = state

	state = len(graph)-1
	for i in range(state, stop-1, -1):
		for j in range(i):
			if (all(any(expr == other for other, *_ in graph[j]) for expr, *_ in graph[i]) and
				all(any(expr == other for other, *_ in graph[i]) for expr, *_ in graph[j])):
				merge(graph, i, j)
				merge(graph, state, i, replace=True)
				state -= 1
				graph.pop()
				break
	return stop


def compile(graph):
	last = None
	state = 0
	t = time()
	while state != last:
		last = state
		state = _compile(graph, last)
	t = time()-t
	print_graph(graph)
	print(t)


def print_graph(graph):
	for i, state in enumerate(graph):
		print(i)
		for expr, transition, *_ in state:
			print(expr, transition)
		print()


def make_graph(*exprs):
	return [[[Family(expr, i), {}] for i, expr in enumerate(exprs)]]


a = Atom("a")
b = Atom("b")
n = 30
m = Repeat(a)
m = Repeat(Choice(a,b),3)
m = Sequence(Repeat(Sequence(a,b),1),a,b)
m = Sequence(b,Repeat(Repeat(a,0,1),2,2),b)
m = Sequence(*[Repeat(a,0,1)]*n, *[a]*n)


graph = make_graph(
	Repeat(a,1),
	Sequence(a,b),
	Repeat(Choice(a,b),1))

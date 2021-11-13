NOT_MATCH = False
HAS_MATCH = True


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
	def __init__(self, *ranges):
		self.ranges = ranges

	def intersect(self, other):
		in_self = []
		in_both = []
		in_other = []
		i = 0
		while True:
			range_self = self.ranges[i]


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
			result.append((None, HAS_MATCH, self.copy()))
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
				if path is None:
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
		return (self.count == other.count or (self.count >= self.min and self.max == NO_MAX)) and self.expr == other.expr

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
			copy.exprs[i] = sub_expr
			if path is None:
				result.extend(copy.advance())
				continue
			result.append((path, status, copy))
		return result

	def reset(self):
		self.cursor = None
		for expr in self.exprs:
			expr.reset()

	def copy(self):
		return Choice(*self.exprs, cursor=self.cursor)

	def __eq__(self, other):
		return self.cursor == other.cursor and self.exprs[self.cursor] == other.exprs[other.cursor]

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
		sub_exprs = self.exprs[self.cursor].advance()
		for path, status, sub_expr in sub_exprs:
			copy = self.copy()
			copy.exprs[self.cursor] = sub_expr
			if status == HAS_MATCH:
				copy.cursor += 1
			if copy.cursor == len(self.exprs):
				result.append((path, HAS_MATCH, copy))
				continue
			if path is None:
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
		return self.cursor == other.cursor and self.exprs[self.cursor] == other.exprs[other.cursor]

	def __repr__(self):
		return '('+''.join(
			f'[{expr}]' if i == self.cursor else
			f'{expr}' for i, expr in enumerate(self.exprs)
		)+')'


a = Atom("a")
b = Atom("b")
n = 10
m = Sequence(Repeat(Sequence(a,b),1),a,b)
m = Sequence(b,Repeat(Repeat(a,0,1),2,2),b)
m = Sequence(*[Repeat(a,0,1)]*n, *[a]*n)

def compile(graph, state=0):
	stop = len(graph)
	for i in range(state, stop):
		exprs = graph[i]
		transitions = {}
		for j, (expr, transition, *_) in enumerate(exprs):
			if transition is not False:
				continue
			exprs[j][1] = {}
			sub_exprs = expr.advance()
			for path, status, sub_expr in sub_exprs:
				if path is None:
					exprs.append([sub_expr, status])
					continue
				path = path.char_min
				if path in transitions:
					if all(sub_expr != other for other, *_ in graph[transitions[path]]):
						graph[transitions[path]].append([sub_expr, status])
				else:
					state = len(graph)
					graph.append([[sub_expr, status]])
				exprs[j][1][path] = transitions[path] = state
	for i, state in enumerate(graph):
		print(i)
		for entry in state:
			print(entry)
		print()
	return stop
graph = [[[m, False]]]

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


class Atom(Regex):
	def __init__(self, char):
		self.char = char

	def advance(self):
		return [(Range(self.char), HAS_MATCH, self)]

	def __repr__(self):
		return f'{self.char}'


NO_MAX = ""
class Repeat(Regex):
	def __init__(self, expr, min=0, max=NO_MAX, count=0):
		self.expr = expr
		self.min = min
		self.max = max
		self.count = count

	def advance(self):
		result = []
		sub_exprs = self.expr.advance()
		for path, status, sub_expr in sub_exprs:
			copy = self.copy()
			copy.expr = sub_expr
			if status == HAS_MATCH:
				copy.expr.reset()
				copy.count += 1
			if copy.count == self.max:
				result.append((path, HAS_MATCH, copy))
			elif copy.count >= self.min:
				result.append((path, HAS_MATCH, copy))
				result.append((path, NOT_MATCH, copy.copy()))
			else:
				result.append((path, NOT_MATCH, copy))
		return result

	def reset(self):
		self.count = 0
		self.expr.reset()

	def copy(self):
		return Repeat(self.expr, min=self.min, max=self.max, count=self.count)

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
			result.append((path, status, copy))
		return result

	def reset(self):
		self.cursor = None
		for expr in self.exprs:
			expr.reset()

	def copy(self):
		return Choice(*self.exprs, cursor=self.cursor)

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
			else:
				result.append((path, NOT_MATCH, copy))
		return result

	def reset(self):
		self.cursor = 0
		for expr in self.exprs:
			expr.reset()

	def copy(self):
		return Sequence(*self.exprs, cursor=self.cursor)

	def __repr__(self):
		return '('+''.join(
			f'[{expr}]' if i == self.cursor else
			f'{expr}' for i, expr in enumerate(self.exprs)
		)+')'


m = Sequence(Repeat(Sequence(Atom("a"), Atom("b")), 1), Atom("a"), Atom("b"))

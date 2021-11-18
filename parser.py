from regex import CharSet, Atom, Repeat, Choice, Sequence


class ParsingError(Exception):
	def __init__(self, msg, position):
		super().__init__()
		self.msg = msg
		self.position = position

	def unquantifiable(position):
		return ParsingError("Preceding token is not quantifiable", position)

	def unexpected(char, position):
		return ParsingError(f"Unexpected token: {repr(char)}")


def parse_choice(text, i):
	expr, i = parse_expr(text, i, True)
	exprs = [expr]
	while True:
		char = text[i]
		i += 1
		if char == ")":
			if len(exprs) == 1:
				return expr, i
			return Choice(*exprs), i
		if char == "|":
			expr, i = parse_expr(text, i, True)
			exprs.append(expr)


def parse_charset(text, i):
	inverted = False
	if text[i] == "^":
		inverted = True
		i += 1
	ranges = []
	escaped = False
	current = None
	ranged = False

	def append(ranges, current, char, ranged):
		if ranged:
			if char is None:
				ranges.extend((ord(current), ord("-")))
			else:
				ranges.append((ord(current), ord(char)))
			return None
		if current is not None:
			ranges.append(ord(current))
		return char

	while True:
		char = text[i]
		i += 1
		if not escaped:
			if char == "]":
				append(ranges, current, None, ranged)
				return Atom(*ranges, inverted=inverted), i
			if char == "\\":
				escaped = True
				continue
			if char == "-" and not ranged:
				if current is None:
					current = char
				else:
					ranged = True
				continue
		current = append(ranges, current, char, ranged)
		ranged = False
		escaped = False


def parse_sequence(text, i=0, in_choice=False):
	escaped = False
	result = []
	current = None
	while True:
		if i >= len(text):
			if current is not None:
				result.append(current)
			if len(result) == 1:
				return result[0], i
			return Sequence(*result), i
		char = text[i]
		i += 1
		if not escaped:
			if char == "\\":
				escaped = True
				continue
			if char == ".":
				if current is not None:
					result.append(current)
				current = [True]
				continue
			if char == "[":
				if current is not None:
					result.append(current)
				current, i = parse_charset(text, i)
				continue
			if char == "(":
				if current is not None:
					result.append(current)
				current, i = parse_choice(text, i)
				continue
			if char == "*":
				if current is None:
					raise ParsingError.unquantifiable(i)
				result.append(Repeat(current, 0, Repeat.NO_MAX))
				current = None
				continue
			if char == "+":
				if current is None:
					raise ParsingError.unquantifiable(i)
				result.append(Repeat(current, 1, Repeat.NO_MAX))
				current = None
				continue
			if char == "?":
				if current is None:
					raise ParsingError.unquantifiable(i)
				result.append(Repeat(current, 0, 1))
				current = None
				continue
			if char == "{":
				if current is None:
					raise ParsingError.unquantifiable(i)
				min, max, i = parse_repeat(text, i)
				result.append(Repeat(current, min, max))
				current = None
				continue
			if char == ")" or (char == "|" and in_choice):
				if current is not None:
					result.append(current)
				if len(result) == 1:
					return result[0], i-1
				return Sequence(*result), i-1
		if current is not None:
			result.append(current)
		current = char
		escaped = False


def parse_repeat(text, i=0):
	min = 0
	max = None
	num = 0
	reset = True
	comma = False
	while True:
		char = text[i]
		i += 1
		if char in "0123456789":
			reset = False
			num *= 10
			num += int(char)
			continue
		if char == ",":
			if comma:
				raise ParsingError.unexpected(char, i)
			min = num
			reset = True
			num = 0
			comma = True
			continue
		if char == "}":
			if comma:
				max = Repeat.NO_MAX if reset else num
			else:
				min = max = num
			return min, max, i
		raise ParsingError.unexpected(char, i)


def parse_expr(text, i=0, in_choice=False):
	char = text[i]
	if char == "(":
		return parse_choice(text, i+1)
	if char == "[":
		return parse_charset(text, i+1)
	return parse_sequence(text, i, in_choice)


def parse_regex(text):
	try:
		expr, i = parse_sequence(text)
		if i < len(text):
			raise ParsingError.unexpected(text[i], i)
		return expr
	except ParsingError as error:
		print(error.msg)
		print(text)
		print(" "*(error.position-1)+"^")
		return None

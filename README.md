# RegExperimentation
This is a little experiment on a regular expression implementation.

As one would expect, a regular expression is compiled into a finite automata. But the procedure is constructed in such a way that it is possible to compile multiple regular expressions into a single automata with multiple acceptance states. This could be useful for generating efficient lexers.

## Pros
This algorithm should always produce:
 - the smallest automata possible
 - the same automata for equivalent regular expressions

## Cons
This algorithm:
 - doesn't support properly non-greedy modifiers
 - doesn't deal with epsilon properly

## Complexity
This project was started thinking that it would fail, few reflections were put in place to optimize it and its complexity was not thouroughly examined. However, it seems like the run time for building an automata is superlinear and matching a string is stricly linear.

## Example
Here is a simple exemple of an automata that matches `if`, `else`, `elif` and variable names (`[_a-zA-Z][_a-zA-Z0-9]*`):

```py
graph = RegexGraph(
	parse_regex("if"),
	parse_regex("elif"),
	parse_regex("else"),
	parse_regex("[_a-zA-Z][_a-zA-Z0-9]*"))

graph.compile()
graph.aggregate()	# simplifies the automata as much as possible

m1 = graph.match(to_ascii("if (true) {}"))
m2 = graph.match(to_ascii("else if (true) {}"))
m3 = graph.match(to_ascii("else_condition = true;")
m4 = graph.match(to_ascii("42")
```

Results:
```py
>>> print(m1)
 if (true) {}
 ~^
matches:
 - if
 - [_a-zA-Z][_a-zA-Z0-9]*

>>> print(m2)
 else if (true) {}
 ~~~^
matches:
 - else
 - [_a-zA-Z][_a-zA-Z0-9]*

>>> print(m3)
 else_condition = true;
 ~~~~~~~~~~~~~^
matches:
 - [_a-zA-Z][_a-zA-Z0-9]*

>>> print(m4)
None
```

As expected `[_a-zA-Z][_a-zA-Z0-9]*` matches the other 3 regular expressions. The RegexGraph object can automatically repport such ambiguity:
```py
>>> graph.analyse()
Ambiguous expressions:
 - if
 - [_a-zA-Z][_a-zA-Z0-9]*
can all be matched by: if

Ambiguous expressions:
 - else
 - [_a-zA-Z][_a-zA-Z0-9]*
can all be matched by: else

Ambiguous expressions:
 - elif
 - [_a-zA-Z][_a-zA-Z0-9]*
can all be matched by: elif
```

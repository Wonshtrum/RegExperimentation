from regex import RegexGraph, to_string, to_ascii
from parser import parse_regex


n = 30
r = parse_regex("a{3,}")			#Repeat(a,3)
r = parse_regex("(a|b)*")			#Repeat(Choice(a,b),0)
r = parse_regex("(ab{})*")			#Repeat(Sequence(a,Repeat(b,0,0)),0)
r = parse_regex("(ab)+ab")			#Sequence(Repeat(Sequence(a,b),1),a,b)
r = parse_regex("b(a?){2}b")		#Sequence(b,Repeat(Repeat(a,0,1),2,2),b)
r = parse_regex("ba{,2}b")			#Sequence(b,Repeat(a,0,2),b)
r = parse_regex("a?"*n+"a"*n)		#Sequence(*[Repeat(a,0,1)]*n, *[a]*n)
r = parse_regex("[abc]*ab")			#Sequence(Repeat(Choice(a,b,c),0),a,b)

graph = RegexGraph(
	parse_regex("b(a?){2}b"),
	parse_regex("ba{,2}b"))

graph = RegexGraph(
	parse_regex("a+"),
	parse_regex("ab"),
	parse_regex("(a|b)+"))

graph = RegexGraph(
	parse_regex("[a-zA-Z_][a-zA-Z0-9_]*"),
	parse_regex(r'"(\\.|[^"\\])*"'),
	parse_regex("[0-9]+"),
	parse_regex("[ \t\r\n]+"),
	parse_regex("//.*?(\n|$)"),
	parse_regex("/\*.*?\*/"),
)

graph = RegexGraph(parse_regex("a*?a"))

graph.compile()
input()
print(graph)
input()
graph.aggregate()
print(graph)
input()
graph.analyse()

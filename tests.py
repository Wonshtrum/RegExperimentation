from regex import make_graph, compile_graph, aggregate_graph, print_graph, analyse_graph, run, run_back, to_string, to_ascii
from parser import parse_regex


n = 30
r = parse_regex("a{3,}")			#Repeat(a,3)
r = parse_regex("(a|b)*")			#Repeat(Choice(a,b),0)
r = parse_regex("(ab{})*")			#Repeat(Sequence(a,Repeat(b,0,0)),0)
r = parse_regex("(ab)+ab")			#Sequence(Repeat(Sequence(a,b),1),a,b)
r = parse_regex("b(a?){2}b")		#Sequence(b,Repeat(Repeat(a,0,1),2,2),b)
r = parse_regex("ba{,2}b")			#Sequence(b,Repeat(a,0,2),b)
r = parse_regex("a?"*n+"a"*n)		#Sequence(*[Repeat(a,0,1)]*n, *[a]*n)

graph = make_graph(
	parse_regex("b(a?){2}b"),
	parse_regex("ba{,2}b"))

graph = make_graph(
	parse_regex("a+"),
	parse_regex("ab"),
	parse_regex("(a|b)+"))

#graph = make_graph(r)

compile_graph(graph)
input()
print_graph(graph)
input()
aggregate_graph(graph)
print_graph(graph)
input()
analyse_graph(graph)

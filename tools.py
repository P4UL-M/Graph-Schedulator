from datetime import date
from io import TextIOWrapper
from tabulate import tabulate


class BadFormat(Exception):
    pass


class BadAction(Exception):  # Exception for actions that can't be done on the automaton
    pass


class Task:

    name: str
    predecessors: list[str] = []

    @property
    def nb_predecessors(self):
        return len(self.predecessors)

    def __init__(self, name: str, weight: int, *predecessors: str):
        self.name = name
        self.weight = weight
        self.predecessors = list(predecessors)

    @staticmethod
    def from_line(line: str):
        line = line.strip()
        name, weight, *predecessors = line.split(" ")
        return Task(name, int(weight), *predecessors)

    def __str__(self):
        return f"Task {self.name}"

    def __repr__(self):
        return f"Task {self.name}"

    def __eq__(self, other):
        return self.name == other.name

    def __hash__(self):
        return hash(self.name)


class Graph:

    states: list[Task] = []

    def __init__(self, name):
        self.name = name

    @staticmethod
    def from_file(file: TextIOWrapper) -> "Graph":
        name = file.name.split("/")[-1].split(".")[0].capitalize()
        graph = Graph(name)
        for line in file:
            graph.states.append(Task.from_line(line))
        # append first fictive state and add it to all states with no predecessors
        graph.states.insert(0, Task("0", 0))
        for state in graph.states:
            if state.nb_predecessors == 0 and state.name != "0":
                state.predecessors.append("0")
        # append last fictive state and add it to all states with no successors
        no_successors_states = [_state.name for _state in graph.states if len(graph.get_successors(_state)) == 0]
        graph.states.append(Task(str(len(graph.states)), 0, *no_successors_states))
        graph.validate()
        return graph

    def display(self, style=0) -> None:
        styles = ["fancy_grid", "rounded_grid", "mixed_grid"]
        # make tabular representation of the graph
        tab = []
        for state in self.states:
            predecessors = ", ".join(state.predecessors)
            tab.append([state.name, state.weight,
                        predecessors, state.nb_predecessors])
        print(tabulate(tab, headers=[
              "Name", "Weight", "Predecessors", "Nb predecessors"], tablefmt=styles[style]))

    def validate(self) -> bool:
        # Check if there is negative edges
        for state in self.states:
            if state.weight < 0:
                raise BadFormat(f"Task {state.name} has a negative weight.")
        # Check if all predecessors exist
        for state in self.states:
            for pred in state.predecessors:
                if pred not in [state.name for state in self.states]:
                    raise BadFormat(f"Task {state.name} has a predecessor {pred} that doesn't exist in the graph.")
        # Check if there is a cycle
        visited: set[Task] = set()
        stack: list[Task] = []
        stack.append(self.states[0])
        while stack:
            state = stack.pop()
            if state not in visited:
                visited.add(state)
                for pred in state.predecessors:
                    stack.append(
                        [state for state in self.states if state.name == pred][0])
            else:
                raise BadFormat(f"Task {state.name} has a cycle.")
        return True

    def ranks(self) -> dict[Task, int]:
        # calculate the ranks of each state
        ranks = {state: 0 for state in self.states}
        for state in self.states:
            for pred in state.predecessors:
                ranks[state] = max(ranks[state], ranks[[state for state in self.states if state.name == pred][0]] + 1)
        return ranks

    def matrix(self) -> tuple[tuple[str]]:
        # make matrix representation of the graph
        matrix = []
        for state in self.states:
            row = ['*' for _ in range(len(self.states))]
            for i, _state in enumerate(self.states):
                if state.name in _state.predecessors:
                    row[i] = state.weight
                # if state in self.get_successors(_state):
                #     row[i] = _state.weight
            matrix.append(tuple(row))
        return tuple(matrix)

    def get_successors(self, state: Task):
        return [_state for _state in self.states if state.name in _state.predecessors]


class Calendar:

    graph = None

    def __init__(self, graph: Graph):
        self.graph = graph

    def display(self, style=0) -> None:
        self.graph.display(style)

    def earliest_date(self) -> dict[Task, int]:
        ranks = self.graph.ranks()
        dates = {state: 0 for state in self.graph.states}
        for state in self.graph.states:
            for succ in self.graph.get_successors(state):
                dates[succ] = max(dates[succ], dates[state] + state.weight)
        return dates

    def latest_date(self) -> dict[Task, int]:
        ranks = self.graph.ranks()
        dates = {state: 0 for state in self.graph.states}
        # make a list of states sorted by ranks in descending order
        states = sorted(self.graph.states, key=lambda x: ranks[x], reverse=True)
        dates[states[0]] = self.earliest_date()[states[0]]
        # for state in states[1:]:
        #     dates_successors = [dates[succ] for succ in self.graph.get_successors(state)]
        #     dates[state] = min(dates_successors) - state.weight
        # TODO: finish this function
        return dates

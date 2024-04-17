from io import TextIOWrapper
from tabulate import tabulate
from typing import Union
from logger import print


class BadFormat(SystemExit):
    pass


class BadAction(SystemExit):  # Exception for actions that can't be done on the automaton
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
        state = self.has_cycle()
        if state:
            raise BadFormat(f"Task {state.name} has a cycle.")
        return True

    def has_cycle(self) -> Union[Task, bool]:
        # Check if there is a cycle in the graph
        visited = set()
        stack = set()
        for state in self.states:
            _state = self._has_cycle(state, visited, stack)
            if _state:
                return _state
        return False

    def _has_cycle(self, state: Task, visited: set[Task], stack: set[Task]) -> Union[Task, bool]:
        if state in stack:
            return state
        if state in visited:
            return False
        visited.add(state)
        stack.add(state)
        for succ in self.get_successors(state):
            _succ = self._has_cycle(succ, visited, stack)
            if _succ:
                return _succ
        stack.remove(state)
        return False

    def ranks(self) -> dict[Task, int]:
        ranks = {state: 0 for state in self.states}
        ranks = self._state_rank(self.states[0], 0, ranks)
        return ranks

    def _state_rank(self, state: Task, current_rank: int, current_ranks: dict[Task, int]) -> dict[Task, int]:
        # print("at state", state, current_rank)
        if current_ranks[state] < current_rank:
            current_ranks[state] = current_rank
        for succ in self.get_successors(state):
            current_ranks = self._state_rank(succ, current_rank + 1, current_ranks)
        # print("returning")
        return current_ranks

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

    def get_critical_path(self) -> list[Task]:
        # take the path with the float equal to 0 for each state
        critical_path = []
        float_dates = Calendar(self).float()
        start = self.states[0]
        critical_path.append(start)
        while start != self.states[-1]:
            for succ in self.get_successors(start):
                if float_dates[succ] == 0:
                    critical_path.append(succ)
                    start = succ
                    break
        return critical_path


class Calendar:

    graph = None

    def __init__(self, graph: Graph):
        self.graph = graph

    def display(self, style=0) -> None:
        self.graph.display(style)

    def earliest_date(self) -> dict[Task, int]:
        ranks = self.graph.ranks()
        ranks = dict(sorted(ranks.items(), key=lambda item: item[1]))  # ? states iteration must be in ascending order of ranks
        dates = {state: 0 for state in self.graph.states}
        for state in ranks.keys():
            for succ in self.graph.get_successors(state):
                dates[succ] = max(dates[succ], dates[state] + state.weight)
        return dates

    def latest_date(self) -> dict[Task, int]:
        ranks = self.graph.ranks()
        dates = {state: 0 for state in self.graph.states}
        # make a list of states sorted by ranks in descending order
        states = sorted(self.graph.states, key=lambda x: ranks[x], reverse=True)
        dates[states[0]] = self.earliest_date()[states[0]]
        for state in states[1:]:
            dates_successors = [dates[succ] for succ in self.graph.get_successors(state)]
            dates[state] = min(dates_successors) - state.weight
        return dates

    def float(self) -> dict[Task, int]:
        # make a list of states sorted by ranks in descending order
        ranks = self.graph.ranks()
        states = sorted(self.graph.states, key=lambda x: ranks[x], reverse=True)
        dates = {state: 0 for state in self.graph.states}
        latest_dates = self.latest_date()
        earliest_dates = self.earliest_date()
        for state in states:
            dates[state] = latest_dates[state] - earliest_dates[state]
        return dates

from io import TextIOWrapper

# Exception for async automaton in functions that don't work with them


class BadFormat(Exception):
    pass


class BadAction(Exception):  # Exception for actions that can't be done on the automaton
    pass


class Task:

    name: str
    predecessors: list[str] = []

    def __init__(self, name: str, weight: int, *predecessors: str):
        self.name = name
        self.weight = weight
        self.predecessors = predecessors

    @staticmethod
    def from_line(line: str):
        line = line.strip()
        name, weight, *predecessors = line.split(" ")
        return Task(name, int(weight), *predecessors)

    def __str__(self):
        return f"Task {self.name} with cost {self.weight}."

    def __repr__(self):
        return f"Task {self.name} with cost {self.weight}."

    def __eq__(self, other):
        return self.name == other.name

    def __hash__(self):
        return hash(self.name)


class Graph:

    states: list[Task] = []

    def __init__(self, name):
        self.name = name

    @staticmethod
    def from_file(file: TextIOWrapper):
        name = file.name.split("/")[-1].split(".")[0].capitalize()
        graph = Graph(name)
        for line in file:
            graph.states.append(Task.from_line(line))
        graph.validate()
        return graph

    def __str__(self):
        return f"Graph {self.name} with {len(self.states)} states.\n" + "\n".join(str(state) for state in self.states)

    def validate(self):
        # Check if there is negative edges
        for state in self.states:
            for pred in state.predecessors:
                if pred not in [state.name for state in self.states]:
                    raise BadFormat(f"Task {state.name} has a predecessor {
                                    pred} that doesn't exist in the graph.")
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

    def ranks(self):
        ranks = {state: 0 for state in self.states}
        for state in self.states:
            for pred in state.predecessors:
                ranks[state] = max(
                    ranks[state], ranks[[state for state in self.states if state.name == pred][0]] + 1)
        return ranks

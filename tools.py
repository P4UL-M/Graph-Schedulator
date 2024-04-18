from io import TextIOWrapper
from tabulate import tabulate
from typing import Union
from logger import print, Settings
import matplotlib.pyplot as plt
from matplotlib.ticker import MaxNLocator


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
                if Settings.verbose:
                    print(f"Task {state.name} has a negative weight.")
                    exit()
                else:
                    raise BadFormat(f"Task {state.name} has a negative weight.")
        # Check if all predecessors exist
        for state in self.states:
            for pred in state.predecessors:
                if pred not in [state.name for state in self.states]:
                    if Settings.verbose:
                        print(f"Task {state.name} has a predecessor {pred} that doesn't exist in the graph.")
                        exit()
                    else:
                        raise BadFormat(f"Task {state.name} has a predecessor {pred} that doesn't exist in the graph.")
        # Check if there is a cycle
        state = self.has_cycle()
        if state:
            if Settings.verbose:
                print(f"Task {state.name} has a cycle.")
                exit()
            else:
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
        float_dates = Calendar(self).float()
        ranks = self.ranks()
        return self._get_critical_path(self.states[0], float_dates, ranks)

    def _get_critical_path(self, state: Task, float_dates: dict[Task, int], ranks: dict[Task, int]) -> Union[list[Task], None]:
        if state == self.states[-1]:
            return [state]
        for succ in self.get_successors(state):
            if float_dates[succ] == 0 and ranks[succ] == ranks[state] + 1:
                critical_path = self._get_critical_path(succ, float_dates, ranks)
                if critical_path:
                    return [state] + critical_path
        return None


class Calendar:

    graph = None

    def __init__(self, graph: Graph):
        self.graph = graph

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

    def display(self) -> None:
        # Get earliest and latest dates
        earliest_dates = self.earliest_date()
        latest_dates = self.latest_date()

        # Extract task names and their start times
        tasks = [task for task in earliest_dates]
        start_times_earliest = [earliest_dates[task] for task in earliest_dates]
        start_times_latest = [latest_dates[task] for task in latest_dates]

        # Calculate durations of tasks
        durations = [task.weight for task in earliest_dates]

        # Remove the first and last tasks
        tasks = tasks[1:-1]
        start_times_earliest = start_times_earliest[1:-1]
        start_times_latest = start_times_latest[1:-1]
        durations = durations[1:-1]

        # end date of each task
        end_dates = [start + duration for start, duration in zip(start_times_earliest, durations)]
        last_end_date = max(end_dates)

        # critical path
        critical_path = self.graph.get_critical_path()

        # Create Gantt chart
        fig, ax = plt.subplots()

        # Plot earliest date bars (blue)
        for i, task in enumerate(tasks):
            # if the task is in the critical path, color it in green
            if task in critical_path:
                ax.barh(task.name + ' (Critical)', durations[i], left=start_times_earliest[i], color='lightgreen')
            else:
                ax.barh(task.name + ' (Earliest)', durations[i], left=start_times_earliest[i], color='skyblue')
            # ax.barh(task + ' (Earliest)', durations[i], left=start_times_earliest[i], color='skyblue')
            ax.barh(task.name + ' (Latest)', durations[i], left=start_times_latest[i], color='salmon')

        # Set labels and title
        ax.set_xlabel('Time')
        ax.set_ylabel('Tasks')
        ax.set_title('Gantt Chart - Earliest and Latest Dates')

        # Adjust layout to fit the legend
        plt.tight_layout()
        # Set x-axis to display only integer values
        ax.xaxis.set_major_locator(MaxNLocator(integer=True))

        # Adjust the x-axis ticks to show lines only at the end of each earliest and latest date
        ticks = start_times_earliest
        ticks += start_times_latest
        ticks += [last_end_date]
        # remove duplicates and sort
        ticks = list(set(ticks))
        ticks.sort()
        ax.set_xticks(ticks)

        # set end of x-axis to the last end date
        ax.set_xlim(0, last_end_date)

        # Show plot
        plt.grid(True)
        plt.show()

from io import TextIOWrapper
from pathlib import Path
from tabulate import tabulate
from typing import Union
from logger import print, Settings
import matplotlib.pyplot as plt
from matplotlib.ticker import MaxNLocator
import matplotlib.animation as animation
import graphviz as gv
import os


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
        self.states = []

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
        if Settings.verbose:
            print("Graph doesn't have negative edges.")
        # Check if all predecessors exist
        for state in self.states:
            for pred in state.predecessors:
                if pred not in [state.name for state in self.states]:
                    if Settings.verbose:
                        print(f"Task {state.name} has a predecessor {pred} that doesn't exist in the graph.")
                        exit()
                    else:
                        raise BadFormat(f"Task {state.name} has a predecessor {pred} that doesn't exist in the graph.")
        if Settings.verbose:
            print("All predecessors exist.")
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
        if Settings.verbose:
            print("Checking for cycles in the graph")
        for state in self.states:
            _state = self._has_cycle(state, visited, stack)
            if _state:
                return _state
        return False

    def _has_cycle(self, state: Task, visited: set[Task], stack: set[Task]) -> Union[Task, bool]:
        if Settings.verbose:
            print(f"Checking {state.name}, stack={stack}, visited={visited}")
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
        if Settings.verbose:
            print("Computing ranks")
        ranks = self._state_rank(self.states[0], 0, ranks)
        return ranks

    def _state_rank(self, state: Task, current_rank: int, current_ranks: dict[Task, int]) -> dict[Task, int]:
        if Settings.verbose:
            print(f"Checking {state.name} with current rank {current_rank}")
        if current_ranks[state] < current_rank:
            current_ranks[state] = current_rank
        for succ in self.get_successors(state):
            current_ranks = self._state_rank(succ, current_rank + 1, current_ranks)
        return current_ranks

    def matrix(self) -> tuple[tuple[str]]:
        # make matrix representation of the graph
        matrix = []
        for state in self.states:
            row = ['*' for _ in range(len(self.states))]
            for i, _state in enumerate(self.states):
                if state.name in _state.predecessors:
                    row[i] = state.weight
            matrix.append(tuple(row))
        return tuple(matrix)

    def get_successors(self, state: Task):
        return [_state for _state in self.states if state.name in _state.predecessors]

    def get_critical_path(self) -> list[Task]:
        gen = self.get_critial_paths()
        return next(gen)

    def get_fast_critical_path(self) -> list[Task]:
        float_dates = Calendar(self).float()
        ranks = self.ranks()
        return self._get_fast_critial_paths(self.states[0], float_dates, ranks)

    def _get_fast_critial_paths(self, state: Task, float_dates: dict[Task, int], ranks: dict[Task, int]):
        if state == self.states[-1]:
            return [state]
        for succ in sorted(self.get_successors(state), key=lambda x: ranks[x]):  # ? sort the successors by rank so we doesn't skip a state with a lower rank in our successors
            if float_dates[succ] == 0:
                critical_path = self._get_fast_critial_paths(succ, float_dates, ranks)
                if critical_path:
                    return [state] + critical_path

    def get_critial_paths(self):
        # take the path with the float equal to 0 for each state
        float_dates = Calendar(self).float()
        earliest_dates = Calendar(self).earliest_date()
        end_dates = [earliest_date + state.weight for state, earliest_date in earliest_dates.items()]
        end_date = max(end_dates)
        ranks = self.ranks()
        for path in self._get_critial_paths(self.states[0], float_dates, ranks):
            # ? check if the path has the same weight as the end date since the rank jump security have been removed
            if sum([state.weight for state in path]) == end_date:
                yield path

    def _get_critial_paths(self, state: Task, float_dates: dict[Task, int], ranks: dict[Task, int]):
        if state == self.states[-1]:
            yield [state]
        for succ in self.get_successors(state):
            # ? useless to check the path if the float is not 0
            if float_dates[succ] == 0:
                for critical_path in self._get_critial_paths(succ, float_dates, ranks):
                    # ? return the path only if we have a complete path
                    if critical_path:
                        yield [state] + critical_path

    def display_graph(self):
        # display the graph using graphviz
        # color the critical path in red
        critical_path = [*self.get_critial_paths()]
        graph = gv.Digraph(self.name)
        for state in self.states:
            if any([state in path for path in critical_path]):
                graph.node(state.name, color='red')
            else:
                graph.node(state.name)
        for state in self.states:
            for succ in self.get_successors(state):
                # check if the edge is in the critical path
                # for one path the condition is state in critical_path and succ in critical_path and critical_path.index(state) == critical_path.index(succ) - 1
                is_critical = any([state in path and succ in path and path.index(state) == path.index(succ) - 1 for path in critical_path])
                graph.edge(state.name, succ.name, label=str(state.weight), color='red' if is_critical else 'black')
        graph.view(cleanup=True)


class Calendar:

    graph = None

    def __init__(self, graph: Graph):
        self.graph = graph

    def earliest_date(self) -> dict[Task, int]:
        ranks = self.graph.ranks()
        ranks = dict(sorted(ranks.items(), key=lambda item: item[1]))  # ? states iteration must be in ascending order of ranks
        dates = {state: 0 for state in self.graph.states}
        if Settings.verbose:
            print("Computing earliest dates")
        for state in ranks.keys():
            if Settings.verbose:
                print(f"Checking {state.name}")
            for succ in self.graph.get_successors(state):
                if Settings.verbose:
                    print(f"Checking constraint for {state.name} -> {succ.name}")
                dates[succ] = max(dates[succ], dates[state] + state.weight)
        return dates

    def latest_date(self) -> dict[Task, int]:
        ranks = self.graph.ranks()
        dates = {state: 0 for state in self.graph.states}
        # ? List of states must be sorted by ranks in descending order
        states = sorted(self.graph.states, key=lambda x: ranks[x], reverse=True)
        dates[states[0]] = self.earliest_date()[states[0]]
        if Settings.verbose:
            print("Computing latest dates")
        for state in states[1:]:
            dates_successors = [dates[succ] for succ in self.graph.get_successors(state)]
            dates[state] = min(dates_successors) - state.weight
            if Settings.verbose:
                print(f"Checking {state.name} with dates {dates_successors} and new date {dates[state]}")
        return dates

    def float(self) -> dict[Task, int]:
        dates = {state: 0 for state in self.graph.states}
        latest_dates = self.latest_date()
        earliest_dates = self.earliest_date()
        if Settings.verbose:
            print("Computing float")
        for state in self.graph.states:
            dates[state] = latest_dates[state] - earliest_dates[state]
            if Settings.verbose:
                print(f"Checking {state.name} with earliest date {earliest_dates[state]} and latest date {latest_dates[state]}")
        return dates

    def free_float(self) -> dict[Task, int]:
        # float but without affecting the earliest date of the successors
        dates = {state: 0 for state in self.graph.states}
        earliest_dates = self.earliest_date()
        for state in self.graph.states:
            dates[state] = min([earliest_dates[succ] - (earliest_dates[state] + state.weight) for succ in self.graph.get_successors(state)] or [0])
        return dates

    def display(self, all_critical_paths_display=False) -> None:
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
                ax.barh(task.name + ' (Earliest)', durations[i], left=start_times_earliest[i], color='lightgreen')
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

        # make animation of the critical path if the user wants to
        if all_critical_paths_display:
            paths = self.graph.get_critial_paths()
            # export to list
            paths = list(paths)

            def animate(frame, paths: list[list[Task]], ax):
                # choose the path to display in fonction of the frame
                current_path = paths[frame % len(paths)]
                # associate each task to its bar
                bars = ax.patches
                # remove the latest date bars
                bars = bars[::2]
                # change the color of each bar in earliest date to skyblue
                for bar, task in zip(bars, tasks):
                    if task in current_path:
                        bar.set_facecolor('lightgreen')
                    else:
                        bar.set_facecolor('skyblue')

            # add the animation to the plot
            ani = animation.FuncAnimation(fig, animate, fargs=(paths, ax), interval=2000, cache_frame_data=False)

        plt.grid(True)
        plt.show()


def clean_up(path: Path):
    # remove the graph file
    for file in path.rglob("*.gv.pdf"):
        os.remove(file)

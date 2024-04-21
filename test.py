from time import time
from pathlib import Path
from InquirerPy import inquirer
from art import *
from logger import Settings, print
from tools import *
from tabulate import tabulate

styles = ["fancy_grid", "rounded_grid", "mixed_grid"]

path = Path(__file__).parent

if __name__ == '__main__':
    tprint("Graph\n Schedulator\n", font="tarty1",
           chr_ignore=True, decoration="block")
    print("By Paul Mairesse, Axel Loones, Louis Le Meilleur & Joseph Benard")

    Settings.debug = True
    Settings.verbose = False

    # Colors
    RED = "\033[1;31m" if not Settings.debug else ""
    GREEN = "\033[1;32m" if not Settings.debug else ""
    YELLOW = "\033[1;33m" if not Settings.debug else ""
    BLUE = "\033[1;34m" if not Settings.debug else ""
    MAGENTA = "\033[1;35m" if not Settings.debug else ""
    CYAN = "\033[1;36m" if not Settings.debug else ""
    WHITE = "\033[1;37m" if not Settings.debug else ""
    BOLD = "\033[1m" if not Settings.debug else ""
    UNDERLINE = "\033[4m" if not Settings.debug else ""
    RESET = "\033[0m" if not Settings.debug else ""

    input_folder = path / "data"
    files_path = [*map(lambda x: x.relative_to(input_folder), filter(lambda x: x.is_file(), input_folder.rglob("*.txt")))]

    Settings.path = path / "outputs"

    for file in files_path:
        Settings.outfile = file
        print("File chosen : ", file)

        with open(input_folder / file, "r") as file:
            try:
                mygraph = Graph.from_file(file)
            except BadFormat as e:
                print(e)
                print("Goodbye !")
                continue
            print("Graph created")
            mygraph.display(1)
            # tabulate with the matrix header are the states and rows names are the states
            table = mygraph.matrix()
            # convert to list
            table = list(map(list, table))
            # put color on numbers
            for i, row in enumerate(table):
                table[i] = list(map(lambda x: CYAN + str(x) + RESET if x.__class__ == int else x, row))
            print(tabulate(table, headers=[RED + BOLD + state.name + RESET for state in mygraph.states], showindex=[RED + BOLD + state.name + RESET for state in mygraph.states], tablefmt="rounded_grid"))

            # create a calander object
            calander = Calendar(mygraph)

            # make a table with the following columns : rank, state, earliest date, latest date
            ranks = mygraph.ranks()
            earliest_dates = calander.earliest_date()
            latest_dates = calander.latest_date()
            float_dates = calander.float()
            free_float_dates = calander.free_float()
            # order the dictionary by ranks
            ranks = dict(sorted(ranks.items(), key=lambda item: item[1]))
            table = [
                list(ranks.values()),
                [state.name for state in ranks.keys()],
                [state.weight for state in ranks.keys()],
                [earliest_dates[state]
                 for state in ranks.keys()],
                [latest_dates[state]
                 for state in ranks.keys()],
                [float_dates[state] for state in ranks.keys()],
                [free_float_dates[state] for state in ranks.keys()],
            ]
            index = ["rank", "state", "weight", "earliest date", "latest date", "float", "free float"]
            # put headers in first column
            print(tabulate(table, tablefmt="fancy_grid", showindex=index))
            # print the critical path and its weight
            print("Critical path : ", end=" ")
            print(*mygraph.get_critical_path(), sep=" -> ")
            print("Critical path weight : ", sum(
                [state.weight for state in mygraph.get_critical_path()]))
            #! debug for testing
            if sum([state.weight for state in mygraph.get_critical_path()]) != earliest_dates[mygraph.states[-1]]:
                raise Exception("Critical path weight is not equal to the earliest date of the last state")

            print(UNDERLINE + RED + "All Critical paths :" + RESET)
            for critical in mygraph.get_critial_paths():
                print(" -", end=" ")
                print(*critical, sep=" -> ")

            print("Goodbye !")

    # test execution times of fast critical path vs critical path

    times = {}
    times_fast = {}

    Settings.debug = False

    for file in files_path:
        current_times = []
        current_times_fast = []

        with open(input_folder / file, "r") as f:
            try:
                mygraph = Graph.from_file(f)
            except BadFormat as e:
                continue

            for i in range(100):

                start = time()
                mygraph.get_critical_path()
                current_times.append(time() - start)

                start = time()
                mygraph.get_fast_critical_path()
                current_times_fast.append(time() - start)

        times[file.name] = sum(current_times) / len(current_times)
        times_fast[file.name] = sum(current_times_fast) / len(current_times_fast)

    print(UNDERLINE + RED + "Execution times :" + RESET)
    table = [
        [
            file.name,
            round(times.get(file.name, 1), 5),
            round(times_fast.get(file.name, 1), 5),
            ("+ " + str(round(((times.get(file.name, 1) / times_fast.get(file.name, 1)) - 1) * 100, 1)))
        ]
        for file in files_path
    ]
    print(tabulate(table, headers=["File", "Critical path", "Fast critical path", "ratio"], tablefmt="fancy_grid"))

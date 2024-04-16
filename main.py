from math import e
from pathlib import Path
from InquirerPy import inquirer, get_style
from art import *
from logger import Settings, print
from tools import *
from tabulate import tabulate


styles = ["fancy_grid", "rounded_grid", "mixed_grid"]

path = Path(__file__).parent

if __name__ == '__main__':
    tprint("Graph\n Schedulator\n", font="tarty1",
           chr_ignore=True, decoration="block")
    print("By POOOOL")

    tprint("Settings", chr_ignore=True)
    promt = inquirer.checkbox(
        message="Select the settings",
        choices=["Debug mode", "Verbose mode"],
        raise_keyboard_interrupt=False,
        mandatory=False,
        border=True,
        instruction="Use space to select and enter to confirm",
    ).execute()
    if promt:
        if "Debug mode" in promt:
            # enter path to debug file
            filepath = inquirer.filepath(
                message="Enter the path to the debug file (pass if you want to create a new one)",
                validate=lambda x: Path(
                    x).is_file() and Path(x).suffix == ".txt",
                raise_keyboard_interrupt=False,
                mandatory=False,
                default=str(path / "outputs"),
            ).execute()
            if filepath == None:
                folder = Path(path / "outputs")
                new_file = "debug.txt"
                confirm_promt = inquirer.confirm(message="Do you want to the default file at the location : " + str(
                    folder / new_file), raise_keyboard_interrupt=False, mandatory=False).execute()
                if confirm_promt:
                    open(folder / new_file, "w+")
                    Settings.outfile = new_file
                    Settings.debug = True
                    print("Debug mode enabled")
                else:
                    print("Debug mode disabled")
                    Settings.debug = False
            else:
                Settings.outfile = Path(filepath).relative_to(path)
                Settings.debug = True
                print("Debug mode enabled")
        if "Verbose mode" in promt:
            Settings.verbose = True

    # Menu
    menu_on = True
    while menu_on:  # Menu loop
        folder = Path(path / "data")
        files = [*map(lambda x: x.relative_to(folder),
                      filter(lambda x: x.is_file(), folder.rglob("*.txt")))]
        # This function lists the files in the folder "FA" which contains all the automaton files
        file_chosen = inquirer.fuzzy(
            message="Which file would you like to import :",  # To chose the file to work on
            choices=files,
            default="",
            raise_keyboard_interrupt=False,
            border=True,
        ).execute()

        print("File chosen : ", file_chosen)
        with open(folder / file_chosen, "r") as file:
            menu_on = False
            mygraph = Graph.from_file(file)
            print("Graph created")
            mygraph.display(1)
            # tabulate with the matrix header are the states and rows names are the states
            print(tabulate(mygraph.matrix(), headers=[
                  state.name for state in mygraph.states], showindex=[state.name for state in mygraph.states], tablefmt="rounded_grid"))
            print(mygraph.ranks())
            calander = Calendar(mygraph)

            # make a table with the following columns : rank, state, earliest date, latest date
            ranks = mygraph.ranks()
            earliest_dates = calander.earliest_date()
            latest_dates = calander.latest_date()
            # order the dictionary by ranks
            ranks = dict(sorted(ranks.items(), key=lambda item: item[1]))
            table = [
                ["ranks"] + list(ranks.values()),
                ["states"] + [state.name for state in ranks.keys()],
                ["weights"] + [state.weight for state in ranks.keys()],
                ["earliest date"] + [earliest_dates[state]
                                     for state in ranks.keys()],
                ["latest date"] + [latest_dates[state]
                                   for state in ranks.keys()],
            ]
            # put headers in first column
            print(tabulate(table, tablefmt="fancy_grid"))

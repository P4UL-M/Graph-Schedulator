# Graph Schedulator

## Description

This project is a simple graph schedulator that uses a graph to represent tasks and their dependencies. The graph is implemented using an adjacency list and the scheduling is done using a topological sort algorithm.

## How to use

To use the graph schedulator, you need to create a file with the tasks and their dependencies. The file should be in the following format:

```
task1 weight1
task2 weight2
task3 weight3 predecessor1 predecessor2 ...
task4 weight4 predecessor3 ...
```

Where `task` is the name of the task, `weight` is the time it takes to complete the task and `predecessor` is the name of a task that needs to be completed before the current task. The file should contain one task per line.

To run the graph schedulator, you need to run the following command:

```
python3 main.py
```

The program will ask for the name of the file with the tasks and their dependencies. After that, it will print the tasks, their ranks, the earliest start time, the latest start time, the slack and the critical path.

## Example
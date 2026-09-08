# The standing goal for a loop run

`run-loop.ps1` reads everything under the `## Goal` heading below and passes it
into every session's prompt, where it outranks `NEXT.md`'s ordering. Leave the
section empty and each session takes task 1. `-Goal "..."` on the command line
overrides this file for one run.

Keep it to a few lines, and give it a done-when a session can check with a
command. A goal that cannot be checked never ends the loop, and the run stops
on the session cap instead having no idea whether it got there.

An example, for shape:

    Land T1: the 57 templates become rows in a PSV with a generator, and adding
    a template is one row. Done when `./check.ps1 -Full` is green with
    `examples/named_routes.py`, the bench and the coverage report all running
    from the PSV, and `template_counts()` still says 57.

## Goal

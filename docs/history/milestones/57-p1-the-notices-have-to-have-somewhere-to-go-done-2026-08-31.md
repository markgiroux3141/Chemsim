## P1 -- The notices have to have somewhere to go -- **DONE 2026-08-31**

`build_network` printed to stdout. A mix-anything game generates hundreds of
NOTICE lines per step -- 397 for five reagents at two generations -- and stdout
is not a place a player looks. Both halves are built.

**1. The notices are carried, not moved.** `ReactionNetwork.notices` holds every
string the builder emitted, in order; `Snapshot.notices` publishes them from the
worker thread; the reports panel renders them beneath the vessel's own reports
under a labelled rule. ⚠ The `print` stays -- a validation script and a test
harness both read it -- so the two channels say the same thing and a test asserts
exactly that. `_ExpansionState.report` became `reports` and RETURNS its strings,
because a method that prints can only serve one destination and that is the whole
bug.

⚠ **AND THE PANEL NEEDED A SCROLLBAR, WHICH IS NOT A COSMETIC NOTE.** It was
seven lines tall and now holds four hundred notices: showing the first seven of
four hundred is the same failure as printing them where nobody looks. `_set_text`
also had to stop resetting the scroll position -- it runs on every 120 ms poll,
so a bare delete-and-insert scrolled a reader back to the top before they could
finish a sentence.

**2. The silent coverage limit is closed.** The generation limit broke out of the
expansion loop with a non-empty frontier and said nothing, while `max_species`,
oversize molecules and mixed standard states all reported. It now issues a notice
naming the count and the species, and `ReactionNetwork.unexpanded` carries the
same set as data. The count is promoted into the reports panel's HEADING rather
than left as the last of hundreds of lines, because it is a fact about the flask
rather than a note about it: *this flask has more to give.*

⚠⚠⚠ **AND `validation/playable_levers.py` PANEL 5 CAUGHT P1'S OWN FIRST VERSION
BEING WRONG, WHICH IS THE FINDING WORTH CARRYING.** The first version read the
frontier only on the generation branch. Panel 5 -- extended in this session to
print `notices` and `frontier` columns, which also re-measured the 397 to the
unit -- reported **frontier 0 for every `gens=2` row**, on 400-species networks
that had plainly been truncated:

        gens  charged  species  reactions  seconds  notices  frontier
           1        3       12          4     0.01        1         3
           1        5       45         36     0.62       31        34
           1        8       63         51     0.56       44        49
           1       12       77         67     0.43       44        59
           2        3       12          8     0.02        0         0
           2        5      400        766    12.40      397       355
           2        8      400        755     6.07      406       337
           2       12      400        743     3.99      392       323

**THE BOUND THAT BIT IS NOT ALWAYS THE BOUND THAT WAS DECLARED.** At
`generations=2` the species cap bites first, so the generation branch never runs
-- and a "react further" control reading that empty frontier would have declined
to offer itself on precisely the flask with the most left to give. The frontier
is now taken on either exit and the NOTICE says which bound stopped it. ⚠ Against
a species cap it is a LOWER bound and the cap's notice now says so: the round the
cap interrupted was left unfinished, so combinations of the previous frontier
went untried as well and those species are not in the list. Against a generation
limit -- the case the game runs on every step -- it is exact.

⚠ **A BOUND THAT NEVER BIT MUST STAY SILENT, and that measurement is what makes
the notice mean anything.** `generations=6` on a system that closes in two exits
through the `while` with an empty frontier and says nothing, because it is not an
approximation. A notice keyed on the ARGUMENT rather than the OUTCOME would have
fired on every `refine` round in the project.

⚠⚠ **WHAT P1 FOUND AND DID NOT FIX, AND P4 NEEDS IT: `generations` IS NOT A
`Scenario` FIELD.** `World.__post_init__` builds its network to a fixpoint and
there is no way to ask for one-generation play through the UI at all. So
`Snapshot.unexpanded` is correct and currently always empty in a session. Adding
it is a `Scenario` field, a `to_dict`/`from_dict` pair and a `SAVE_VERSION` bump
-- which P2 is touching anyway for BOTTLE and CHARGE, and which is why it was
left rather than bolted on here.

Suite **1202 passed / 0 failed in 30:52**; `tolerance_audit.py` **10 m 36 s**
and byte-identical to C7's record, nothing moved. Scoreboard unchanged: 21 of
173 playable, 59/240 classes, 38 BOTH.

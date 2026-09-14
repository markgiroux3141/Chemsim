# A class-wide phenol pKa rule is refused, and the table is why

Measured 2026-09-13 by `python validation/pka_domains.py` (~5 s), panels 0 and
4. T5 asked the question and T23 answered it with three more rows, which is the
part worth reading: the rows were written to unblock a player's flask, and they
made the rule *less* supportable, not more.

The carboxylic plateau in `properties/carboxylic_pka.py` is the one rule this
project has, and it exists because five unbranched rows from C3 up span 0.15 pKa
units. Every other acid class in `properties/electrolyte._PAIRS` has been asked
the same question. Amines were refused in T5 on width alone: three rows over
6.04 units, and the one domain that could be carved out holds a single row
against the two `carboxylic_pka.plateau` requires. Mineral oxyacids want no pKa
at all — their gap is neutral thermochemistry, which is T25. That left phenols,
and this is the argument for them.

## The sample, after T23

| sigma_sum | pKa | row |
|---|---|---|
| -2.009 | 10.19 | eugenol |
| -1.698 | 9.54 | coniferyl alcohol |
| -0.920 | 9.95 | phenol |
| -0.920 | 13.40 | salicylic acid, 2nd |
| -0.246 | 7.16 | 4-nitrophenol |

`sigma_sum` is `reactions.hammett.survey` summed over the ring. The class spans
6.24 pKa units over five rows.

## Two counterexamples, and both are inside the sample

**The scale cannot separate two rows 3.45 units apart.** Phenol and salicylic
acid's second proton have the same substituent sum, -0.920, and their measured
acidities differ by 3.45. What holds salicylate's phenol proton is an
intramolecular hydrogen bond to the ortho carboxylate — a through-space
interaction that no sum over substituent constants represents. Any rule reading
a pKa off this scale hands both of them one value and is wrong about one of them
by three and a half decades.

**The scale gets a sign wrong.** 3 of the 10 pairs in the sample are ordered
backwards by the sum: the lower sum is the stronger acid where a monotone rule
requires the weaker. Two of the three are salicylate's second proton again, so
they say nothing new. The third does. Coniferyl alcohol sums to -1.698, well on
the donating side of phenol's -0.920, so a fitted rule predicts it *less* acidic
than phenol; it is measurably *more* acidic, 9.54 against 9.95. The
(E)-propenyl side chain conjugates with the ring and delocalises the phenoxide,
and the pattern set scores it as an insulated alkyl. Eugenol is the control —
same ortho methoxy, but an allyl whose CH2 breaks the conjugation — and it lands
where the sum says it should, at 10.19. One measurement, one control, and the
difference between them is exactly the effect the scale does not carry.

`pka_domains.py` panel 4 derives both of these from the table rather than
asserting them, so each stops being true the day a row makes it untrue.

## The scale is the wrong one, which is the point rather than a caveat

`reactions.hammett` carries sigma-plus, fitted on electrophilic aromatic
substitution rates, with two labelled aqueous proxies. Phenol ionisation is
fitted on sigma-minus, because a phenoxide delocalises its charge onto a para
acceptor directly. Those are different constants for the same substituent, and
the gap between them is largest for exactly the groups the catalog's phenols
carry: nitro, carbonyl, cyano. Adding sigma-minus to `hammett` is a real option;
it is not a line of data, and until it exists no rule fitted here can be quoted.

## How far the gap reaches anyway

77 of the missing phenols carry a ring the survey can read. 30 of them sit
outside the curated -2.009 to -0.246, and 12 carry at least one substituent no
pattern claims — which the panel reports rather than scoring as zero. The
extremes are a catechin at -5.080 and picric acid at +1.102, three and a half
sigma units beyond anything measured here.

## What this leaves

Rows, in the order panel 3 ranks them by route demand, and each with a named
source. That is T23's remaining half: 102 corpus phenol ions over 77 compounds
want a pKa and 20 catalog routes name one of those compounds, with salicylic
acid (4 routes) and vanillin (3) at the head. The refusal above is not an
argument against ever having a phenol rule — it is a statement of what the rule
would need first: sigma-minus in `hammett`, a hydrogen-bond exclusion in the
domain, and a sample that brackets the nitrophenols on both sides.

## 5. ⚠⚠⚠ AN UNPRICEABLE SPECIES CRASHES THE BUILD, AND IT IS REACHABLE IN TWO CLICKS

    picker rows '5-HMF' + 'oxygen', generations=1  ->  ValueError
    no thermochemistry available for 'O=Cc1ccc(C=O)o1': its formation half
    resolved (Benson group additivity) but there is NO physical half

**Both rows are offered ungreyed by the picker, and this is ONE generation.**
The handoff recorded this as *"deeper exploration crashes rather than
degrades"*; that understates it. 5-HMF is priced and chargeable, and the species
it makes -- 2,5-diformylfuran -- has a formation half from Benson and no
physical half, because no measured Tb exists anywhere, so no vapour-pressure
curve can be built and thermochemistry refuses rather than pretending the thing
is non-volatile.

**That refusal is right in isolation and wrong here.** `max_species`,
`max_molar_mass` and `generations` all DROP, NOTICE and carry on. This one
propagated out of `build_network` as a bare `ValueError` and the player got a
traceback. **It is the reason R1 was a prerequisite and not a nice-to-have.**

✔ **CLOSED BY R1, AND THE COUNT IN THIS FINDING IS WRONG BY FOUR.** The
exception reported the first refusal and stopped. With all of them reported it
is **five species from three templates** -- the dialdehyde, its ether dimer and
three bis-furylmethanes -- and with all five refused **the pick has ZERO
reactions**. The engine cannot price any chemistry it can find between 5-HMF and
oxygen, which is a statement about the pick that no traceback could make. See
R1 below.

---

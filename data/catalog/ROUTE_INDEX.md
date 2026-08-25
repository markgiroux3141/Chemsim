# Route index: primary compounds, intermediates and products

173 named routes, 377 steps, 1583 compounds in the catalog.

For each route the three lists below are **derived from the steps**, not declared: a species consumed but never produced inside the route is a *primary feedstock*; one that is both produced and consumed is an *intermediate*; one produced and never consumed is a *product or byproduct*; and one appearing on both sides of a single step is a *catalyst*. See `tools/catalog.py` for why that is derived rather than written down.

The same species is routinely a feedstock in one route and an intermediate in another -- acetaldehyde, phenol and sulfuric acid all are. That is not a conflict; it is the point of indexing them per route. `data/catalog/derived/species_roles.psv` rolls the counts up per species.

## Contents

- **ancient** (15): [limestone calcination and slaking](#lime-cycle), [blast furnace ironmaking](#blast-furnace), [galena roasting and reduction](#lead-smelting), [copper sulfide smelting](#copper-smelting), [mercury from cinnabar](#mercury-from-cinnabar), [black powder](#gunpowder), [white lead by the stack process](#white-lead-route), [vinegar by acetic fermentation](#acetic-fermentation), [soap from fat and lye](#soap-saponification), [ethanol by fermentation](#ethanol-fermentation), [sucrose inversion](#invert-sugar), [indigo from woad and indican](#indigo-natural), [Tyrian purple from murex](#tyrian-purple-route), [vegetable tanning](#tanning-route), [iron gall ink](#iron-gall-ink)
- **alchemical** (4): [distillation of green vitriol](#vitriol-distillation), [nitric acid from saltpetre](#saltpetre-nitric), [aqua regia](#aqua-regia), [vermilion from mercury and sulfur](#vermilion-route)
- **1700s** (6): [lead chamber sulfuric acid](#lead-chamber), [Leblanc soda process](#leblanc-process), [white phosphorus from bone ash](#white-phosphorus), [zinc retort smelting](#zinc-smelting), [Prussian blue](#prussian-blue-route), [destructive distillation of wood](#wood-distillation)
- **1800s** (70): [contact process sulfuric acid](#contact-process), [pyrite roasting to SO2](#pyrite-roasting), [Solvay ammonia-soda process](#solvay-process), [chloralkali electrolysis](#chloralkali), [Deacon chlorine process](#deacon-process), [Weldon chlorine from pyrolusite](#weldon-chlorine), [bleaching powder manufacture](#bleaching-powder), [superphosphate fertiliser](#superphosphate), [strike-anywhere match head](#match-chemistry), [Bayer alumina process](#bayer-process), [Hall-Heroult aluminium](#hall-heroult), [thermite reaction](#thermite), [Castner-Kellner mercury cell](#castner-kellner), [nitroglycerin and dynamite](#nitroglycerin-route), [nitrocellulose / guncotton](#guncotton), [picric acid from phenol](#picric-acid-route), [mercury fulminate](#mercury-fulminate-route), [coal tar fractionation](#coal-tar-distillation), [coal gas and coke](#coal-gas), [nitration of benzene](#benzene-nitration), [aniline from nitrobenzene](#aniline-route), [Perkin mauve](#mauveine-route), [synthetic alizarin](#alizarin-route), [Baeyer-Drewson indigo](#indigo-baeyer-drewson), [Heumann-Pfleger indigo](#indigo-heumann), [diazotisation and azo coupling](#azo-dye-coupling), [malachite green](#triarylmethane-dyes), [chrome yellow](#chrome-yellow-route), [benzenesulfonate alkali fusion](#phenol-sulfonation), [Kolbe-Schmitt salicylic acid](#salicylic-kolbe), [aspirin](#aspirin-route), [phenacetin](#phenacetin-route), [salicin to salicylic acid](#salicin-hydrolysis), [chloroform by the haloform reaction](#chloroform-route), [chloral and chloral hydrate](#chloral-route), [water gas shift](#water-gas-shift), [Kucherov acetylene hydration](#acetylene-acetaldehyde), [calcium carbide and acetylene](#calcium-carbide), [vulcanisation of rubber](#vulcanisation), [viscose rayon](#viscose-route), [celluloid](#celluloid-route), [starch to glucose syrup](#starch-hydrolysis), [vanillin from eugenol](#vanillin-eugenol), [silver halide photography](#photography-silver), [Strecker amino acid synthesis](#strecker-amino-acid), [Gabriel primary amine synthesis](#gabriel-synthesis), [malonic ester synthesis](#malonic-ester-synthesis), [acetoacetic ester synthesis](#acetoacetic-ester-synthesis), [aldol condensation](#aldol-route), [Claisen ester condensation](#claisen-route), [Friedel-Crafts alkylation and acylation](#friedel-crafts-route), [Cannizzaro disproportionation](#cannizzaro-route), [Perkin cinnamic acid synthesis](#perkin-route), [Knoevenagel condensation](#knoevenagel-route), [Beckmann rearrangement](#beckmann-route), [Hofmann rearrangement](#hofmann-route), [Curtius rearrangement](#curtius-route), [Sandmeyer reaction](#sandmeyer-route), [Reimer-Tiemann formylation](#reimer-tiemann), [Williamson ether synthesis](#williamson-ether), [Fischer indole synthesis](#fischer-indole), [Skraup quinoline synthesis](#skraup-route), [Hantzsch dihydropyridine synthesis](#hantzsch-pyridine), [Wohler urea synthesis](#wohler-urea), [Kolbe electrolysis](#kolbe-electrolysis), [iodoform test](#haloform-iodoform), [Fehling reducing sugar test](#fehling-test), [Tollens silver mirror](#tollens-test), [Marsh arsenic test](#marsh-test), [Kjeldahl nitrogen determination](#kjeldahl)
- **1900s** (73): [Claus sulfur recovery](#claus-process), [Haber-Bosch ammonia](#haber-bosch), [Ostwald nitric acid](#ostwald-process), [Birkeland-Eyde arc process](#birkeland-eyde), [Frank-Caro cyanamide process](#frank-caro), [Andrussow HCN process](#andrussow), [sodium hypochlorite bleach](#hypochlorite-bleach), [wet-process phosphoric acid](#phosphoric-wet), [Downs cell sodium](#downs-cell), [TNT manufacture](#tnt-route), [RDX from hexamine](#rdx-route), [PETN from pentaerythritol](#petn-route), [cumene (Hock) process](#phenol-cumene), [Dow chlorobenzene hydrolysis](#phenol-dow), [Bakelite phenolic resin](#bakelite-route), [paracetamol](#paracetamol-route), [sulfanilamide](#sulfa-drug-route), [prontosil](#prontosil-route), [penicillin fermentation and semisynthesis](#penicillin-route), [aspirin hydrolysis and impurities](#aspirin-impurity), [DDT](#ddt-route), [Freon-12 from carbon tetrachloride](#freon-route), [PTFE from chlorodifluoromethane](#ptfe-route), [steam methane reforming](#steam-reforming), [methanol from syngas](#methanol-synthesis), [Fischer-Tropsch synthesis](#fischer-tropsch), [Monsanto / Cativa acetic acid](#monsanto-acetic), [acetic anhydride via ketene](#acetic-anhydride-ketene), [Wacker oxidation](#wacker-process), [steam cracking of naphtha](#steam-cracking), [ethylene oxide by direct oxidation](#ethylene-oxide-route), [chlorohydrin route to ethylene oxide](#chlorohydrin-route), [ethylene glycol by EO hydration](#ethylene-glycol-route), [PET polyester](#pet-route), [Amoco terephthalic acid](#p-xylene-oxidation), [nylon 66](#nylon66-route), [nylon 6 from caprolactam](#nylon6-route), [adipic acid from cyclohexane](#adipic-acid-route), [SOHIO ammoxidation](#acrylonitrile-sohio), [adiponitrile by electrohydrodimerisation](#adiponitrile-route), [vinyl chloride and PVC](#vinyl-chloride-route), [styrene from ethylbenzene](#styrene-route), [polyethylene](#polyethylene-route), [MMA by the acetone cyanohydrin route](#mma-ach), [bisphenol A and polycarbonate](#bisphenol-a-route), [epoxy resin from epichlorohydrin](#epoxy-route), [polyurethane from TDI](#polyurethane-route), [MDI from aniline and formaldehyde](#mdi-route), [urea-formaldehyde resin](#urea-formaldehyde-route), [melamine from urea](#melamine-route), [silicones by the direct process](#silicone-route), [neoprene from acetylene](#neoprene-route), [Buna synthetic rubber from butadiene](#buna-rubber), [hydroformylation (oxo process)](#oxo-process), [2-ethylhexanol by aldol-oxo](#2-ethylhexanol-route), [DOP plasticiser](#dop-route), [phthalic anhydride from o-xylene](#phthalic-anhydride-route), [maleic anhydride from n-butane](#maleic-anhydride-route), [fat hardening](#hydrogenation-margarine), [ethanol by ethylene hydration](#ethanol-hydration), [acetone-butanol-ethanol fermentation](#abe-fermentation), [citric acid by fermentation](#citric-acid-fermentation), [monosodium glutamate](#msg-route), [furfural from pentosans](#furfural-route), [vanillin from lignin](#vanillin-lignin), [vanillin from guaiacol](#vanillin-guaiacol), [synthetic camphor from pinene](#camphor-route), [Reichstein vitamin C synthesis](#vitamin-c-reichstein), [Grignard addition to a carbonyl](#grignard-route), [Wittig olefination](#wittig-route), [Diels-Alder cycloaddition](#diels-alder-route), [Mannich reaction](#mannich-route), [Michael addition and Robinson annulation](#michael-robinson)
- **modern** (5): [biodiesel by transesterification](#biodiesel-route), [glycerol to epichlorohydrin](#glycerol-epichlorohydrin), [lactic acid to polylactide](#lactic-acid-pla), [HMF from fructose](#hmf-route), [menthol from citronellal](#menthol-route)

## ancient

<a id="lime-cycle"></a>

### limestone calcination and slaking

`lime-cycle` &middot; heavy-inorganic &middot; target: calcium oxide `calcium-oxide`

> the mortar cycle

**Primary feedstocks** (0)

- *(none: every species is made inside the route)*

**Intermediates** (5)

- calcium carbonate `calcium-carbonate`
- calcium hydroxide `calcium-hydroxide`
- calcium oxide `calcium-oxide`
- carbon dioxide `carbon-dioxide`
- water `water`

**Products and byproducts** (0)

- *(none)*

| # | step | in | out | conditions | class |
|--:|---|---|---|---|---|
| 1 | calcination | calcium-carbonate | calcium-oxide + carbon-dioxide | kiln, 1200 K | `calcination` |
| 2 | slaking | calcium-oxide + water | calcium-hydroxide | exothermic | `lime-slaking` |
| 3 | carbonation of mortar | calcium-hydroxide + carbon-dioxide | calcium-carbonate + water | months, ambient | `solid-carbonation` |

<a id="blast-furnace"></a>

### blast furnace ironmaking

`blast-furnace` &middot; metallurgy &middot; target: iron metal `iron`

> carbon monoxide reduction of haematite

**Primary feedstocks** (5)

- calcium oxide `calcium-oxide`
- graphite `carbon-graphite`
- iron(III) oxide `iron-iii-oxide`
- dioxygen `oxygen`
- silicon dioxide `silicon-dioxide`

**Intermediates** (3)

- carbon dioxide `carbon-dioxide`
- carbon monoxide `carbon-monoxide`
- iron(II) oxide `iron-ii-oxide`

**Products and byproducts** (2)

- calcium silicate `calcium-silicate`
- iron metal `iron`

| # | step | in | out | conditions | class |
|--:|---|---|---|---|---|
| 1 | coke combustion | carbon-graphite + oxygen | carbon-dioxide | tuyere, 2200 K | `combustion` |
| 2 | Boudouard reaction | carbon-dioxide + carbon-graphite | carbon-monoxide | 1200 K | `boudouard` |
| 3 | indirect reduction | iron-iii-oxide + carbon-monoxide | iron-ii-oxide + carbon-dioxide | stack, 900 K | `gas-solid-reduction` |
| 4 | final reduction | iron-ii-oxide + carbon-monoxide | iron + carbon-dioxide | bosh, 1300 K | `gas-solid-reduction` |
| 5 | slag formation | calcium-oxide + silicon-dioxide | calcium-silicate | hearth | `slagging` |

<a id="lead-smelting"></a>

### galena roasting and reduction

`lead-smelting` &middot; metallurgy &middot; target: lead metal `lead`

> the lead behind the lead chamber

**Primary feedstocks** (3)

- carbon monoxide `carbon-monoxide`
- lead sulfide `lead-sulfide`
- dioxygen `oxygen`

**Intermediates** (1)

- lead(II) oxide `lead-ii-oxide`

**Products and byproducts** (3)

- carbon dioxide `carbon-dioxide`
- lead metal `lead`
- sulfur dioxide `sulfur-dioxide`

| # | step | in | out | conditions | class |
|--:|---|---|---|---|---|
| 1 | galena roasting | lead-sulfide + oxygen | lead-ii-oxide + sulfur-dioxide | sinter plant | `roasting` |
| 2 | oxide reduction | lead-ii-oxide + carbon-monoxide | lead + carbon-dioxide | blast furnace | `gas-solid-reduction` |

<a id="copper-smelting"></a>

### copper sulfide smelting

`copper-smelting` &middot; metallurgy &middot; target: copper metal `copper`

> roast, smelt, convert

**Primary feedstocks** (3)

- carbon monoxide `carbon-monoxide`
- copper(II) sulfide `copper-sulfide`
- dioxygen `oxygen`

**Intermediates** (1)

- copper(II) oxide `copper-ii-oxide`

**Products and byproducts** (3)

- carbon dioxide `carbon-dioxide`
- copper metal `copper`
- sulfur dioxide `sulfur-dioxide`

| # | step | in | out | conditions | class |
|--:|---|---|---|---|---|
| 1 | roasting | copper-sulfide + oxygen | copper-ii-oxide + sulfur-dioxide | roaster | `roasting` |
| 2 | reduction to blister copper | copper-ii-oxide + carbon-monoxide | copper + carbon-dioxide | converter | `gas-solid-reduction` |

<a id="mercury-from-cinnabar"></a>

### mercury from cinnabar

`mercury-from-cinnabar` &middot; metallurgy &middot; target: mercury `mercury`

> roasting to the metal and SO2

**Primary feedstocks** (2)

- mercury(II) sulfide `mercury-sulfide`
- dioxygen `oxygen`

**Intermediates** (0)

- *(none: a single-step route has no intermediate by definition)*

**Products and byproducts** (2)

- mercury `mercury`
- sulfur dioxide `sulfur-dioxide`

| # | step | in | out | conditions | class |
|--:|---|---|---|---|---|
| 1 | cinnabar roasting | mercury-sulfide + oxygen | mercury + sulfur-dioxide | retort, 900 K | `roasting-to-metal` |

<a id="gunpowder"></a>

### black powder

`gunpowder` &middot; energetics &middot; target: black powder marker `gunpowder-marker`

> saltpetre, sulfur, charcoal

**Primary feedstocks** (3)

- graphite `carbon-graphite`
- potassium nitrate `potassium-nitrate`
- sulfur (S8 crown) `sulfur-s8`

**Intermediates** (1)

- black powder marker `gunpowder-marker`

**Products and byproducts** (4)

- carbon dioxide `carbon-dioxide`
- carbon monoxide `carbon-monoxide`
- dinitrogen `nitrogen`
- potassium sulfate `potassium-sulfate`

| # | step | in | out | conditions | class |
|--:|---|---|---|---|---|
| 1 | incorporation | potassium-nitrate + sulfur-s8 + carbon-graphite | gunpowder-marker | wet-milled 75:10:15, corned and dried | `formulation` |
| 2 | deflagration | gunpowder-marker | potassium-sulfate + nitrogen + carbon-dioxide + carbon-monoxide | ignition, self-oxidising | `deflagration` |

<a id="white-lead-route"></a>

### white lead by the stack process

`white-lead-route` &middot; pigments &middot; target: white lead `basic-lead-carbonate`

> vinegar, lead and dung

**Primary feedstocks** (3)

- carbon dioxide `carbon-dioxide`
- lead metal `lead`
- dioxygen `oxygen`

**Intermediates** (3)

- ethanoic acid `acetic-acid`
- lead(II) acetate `lead-acetate`
- water `water`

**Products and byproducts** (1)

- white lead `basic-lead-carbonate`

| # | step | in | out | conditions | class |
|--:|---|---|---|---|---|
| 1 | acetate formation | lead + acetic-acid + oxygen | lead-acetate + water | stack process, dung heat | `oxidative-dissolution` |
| 2 | carbonation | lead-acetate + carbon-dioxide + water | basic-lead-carbonate + acetic-acid | months in the stack | `basic-carbonate-precipitation` |

<a id="acetic-fermentation"></a>

### vinegar by acetic fermentation

`acetic-fermentation` &middot; fermentation &middot; target: ethanoic acid `acetic-acid`

> ethanol plus air over bacteria

**Primary feedstocks** (2)

- ethanol `ethanol`
- dioxygen `oxygen`

**Intermediates** (2)

- ethanal `acetaldehyde`
- hydrogen peroxide `hydrogen-peroxide`

**Products and byproducts** (2)

- ethanoic acid `acetic-acid`
- water `water`

| # | step | in | out | conditions | class |
|--:|---|---|---|---|---|
| 1 | ethanol oxidation | ethanol + oxygen | acetaldehyde + hydrogen-peroxide | Acetobacter, 300 K, aerated | `alcohol-oxidation` |
| 2 | aldehyde oxidation | acetaldehyde + hydrogen-peroxide | acetic-acid + water | same organism | `aldehyde-oxidation` |

<a id="soap-saponification"></a>

### soap from fat and lye

`soap-saponification` &middot; consumer &middot; target: sodium stearate `sodium-stearate`

> the oldest deliberate synthesis

**Primary feedstocks** (3)

- sodium chloride `sodium-chloride`
- sodium hydroxide `sodium-hydroxide`
- glyceryl tristearate `tristearin`

**Intermediates** (0)

- *(none: a single-step route has no intermediate by definition)*

**Products and byproducts** (1)

- 1,2,3-propanetriol `glycerol`

**Catalysts** (both sides of one step, net stoichiometry zero)

- sodium stearate `sodium-stearate`
- water `water`

| # | step | in | out | conditions | class |
|--:|---|---|---|---|---|
| 1 | triglyceride saponification | tristearin + sodium-hydroxide | sodium-stearate + glycerol | 370 K, boiling with lye | `saponification` |
| 2 | graining out | sodium-stearate + sodium-chloride + water | sodium-stearate + water | salting out, phase split | `salting-out` |

<a id="ethanol-fermentation"></a>

### ethanol by fermentation

`ethanol-fermentation` &middot; fermentation &middot; target: ethanol `ethanol`

> sugar to ethanol and CO2

**Primary feedstocks** (2)

- L-isoleucine `isoleucine`
- sucrose `sucrose`

**Intermediates** (4)

- ethanal `acetaldehyde`
- D-glucose `glucose`
- 2-oxopropanoic acid `pyruvic-acid`
- water `water`

**Products and byproducts** (5)

- ammonia `ammonia`
- carbon dioxide `carbon-dioxide`
- ethanol `ethanol`
- D-fructose `fructose`
- 3-methyl-1-butanol `isoamyl-alcohol`

| # | step | in | out | conditions | class |
|--:|---|---|---|---|---|
| 1 | sucrose inversion | sucrose + water | glucose + fructose | invertase or acid | `glycoside-hydrolysis` |
| 2 | glycolysis to pyruvate | glucose | pyruvic-acid + water | yeast, anaerobic | `glycolysis` |
| 3 | decarboxylation | pyruvic-acid | acetaldehyde + carbon-dioxide | pyruvate decarboxylase | `decarboxylation` |
| 4 | reduction to ethanol | acetaldehyde | ethanol | alcohol dehydrogenase, NADH | `biological-reduction` |
| 5 | fusel oil byproducts | isoleucine | isoamyl-alcohol + carbon-dioxide + ammonia | Ehrlich pathway | `biological-transformation` |

<a id="invert-sugar"></a>

### sucrose inversion

`invert-sugar` &middot; food &middot; target: D-fructose `fructose`

> acid or invertase

**Primary feedstocks** (2)

- sucrose `sucrose`
- water `water`

**Intermediates** (0)

- *(none: a single-step route has no intermediate by definition)*

**Products and byproducts** (2)

- D-fructose `fructose`
- D-glucose `glucose`

| # | step | in | out | conditions | class |
|--:|---|---|---|---|---|
| 1 | inversion | sucrose + water | glucose + fructose | acid or invertase | `glycoside-hydrolysis` |

<a id="indigo-natural"></a>

### indigo from woad and indican

`indigo-natural` &middot; dyes &middot; target: indigo `indigo`

> hydrolysis then air oxidation

**Primary feedstocks** (4)

- indican `indican`
- dioxygen `oxygen`
- sodium dithionite `sodium-dithionite`
- sodium hydroxide `sodium-hydroxide`

**Intermediates** (4)

- indigo `indigo`
- leucoindigo `indigo-white`
- indoxyl `indoxyl`
- water `water`

**Products and byproducts** (2)

- D-glucose `glucose`
- sodium bisulfite `sodium-bisulfite`

| # | step | in | out | conditions | class |
|--:|---|---|---|---|---|
| 1 | glycoside hydrolysis | indican + water | indoxyl + glucose | fermentation of the leaves | `glycoside-hydrolysis` |
| 2 | air oxidation | indoxyl + oxygen | indigo + water | beating the vat in air | `oxidative-dimerisation` |
| 3 | vat reduction for dyeing | indigo + sodium-dithionite + sodium-hydroxide | indigo-white + sodium-bisulfite | the soluble leuco form | `reduction` |
| 4 | reoxidation on the fibre | indigo-white + oxygen | indigo + water | hanging the cloth in air | `leuco-dye-oxidation` |

<a id="tyrian-purple-route"></a>

### Tyrian purple from murex

`tyrian-purple-route` &middot; dyes &middot; target: 6,6-dibromoindigo `tyrian-purple`

> the most expensive dye in history

**Primary feedstocks** (2)

- indican `indican`
- dioxygen `oxygen`

**Intermediates** (0)

- *(none: a single-step route has no intermediate by definition)*

**Products and byproducts** (2)

- 6,6-dibromoindigo `tyrian-purple`
- water `water`

| # | step | in | out | conditions | class |
|--:|---|---|---|---|---|
| 1 | enzymatic and photochemical conversion | indican + oxygen | tyrian-purple + water | murex gland, sunlight | `biological-transformation` |

<a id="tanning-route"></a>

### vegetable tanning

`tanning-route` &middot; leather &middot; target: 3,4,5-trihydroxybenzoic acid `gallic-acid`

> tannin hydrolysis

**Primary feedstocks** (2)

- *collagen-marker* (no molecular graph)
- gallotannin core (digalloyl glucose) `tannic-acid-core`

**Intermediates** (2)

- 3,4,5-trihydroxybenzoic acid `gallic-acid`
- water `water`

**Products and byproducts** (2)

- D-glucose `glucose`
- *tanned-leather-marker* (no molecular graph)

| # | step | in | out | conditions | class |
|--:|---|---|---|---|---|
| 1 | tannin hydrolysis | tannic-acid-core + water | gallic-acid + glucose | acid or enzymatic | `ester-hydrolysis` |
| 2 | collagen crosslinking | gallic-acid + collagen-marker | tanned-leather-marker + water | pit tanning, months | `crosslinking` |

<a id="iron-gall-ink"></a>

### iron gall ink

`iron-gall-ink` &middot; consumer &middot; target: *iron-gallate-marker* (no molecular graph)

> gallic acid plus green vitriol

**Primary feedstocks** (4)

- iron(II) sulfate `iron-ii-sulfate`
- dioxygen `oxygen`
- gallotannin core (digalloyl glucose) `tannic-acid-core`
- water `water`

**Intermediates** (1)

- 3,4,5-trihydroxybenzoic acid `gallic-acid`

**Products and byproducts** (3)

- D-glucose `glucose`
- *iron-gallate-marker* (no molecular graph)
- sulfuric acid `sulfuric-acid`

| # | step | in | out | conditions | class |
|--:|---|---|---|---|---|
| 1 | gallotannin hydrolysis | tannic-acid-core + water | gallic-acid + glucose | steeping the galls | `ester-hydrolysis` |
| 2 | complexation and oxidation | gallic-acid + iron-ii-sulfate + oxygen | iron-gallate-marker + sulfuric-acid | air darkens it on the page | `oxidative-complexation` |

## alchemical

<a id="vitriol-distillation"></a>

### distillation of green vitriol

`vitriol-distillation` &middot; heavy-inorganic &middot; target: sulfuric acid `sulfuric-acid`

> the oldest sulfuric acid route

**Primary feedstocks** (2)

- iron(II) sulfate `iron-ii-sulfate`
- water `water`

**Intermediates** (1)

- sulfur trioxide `sulfur-trioxide`

**Products and byproducts** (2)

- iron(II) oxide `iron-ii-oxide`
- sulfuric acid `sulfuric-acid`

| # | step | in | out | conditions | class |
|--:|---|---|---|---|---|
| 1 | dehydration of green vitriol | iron-ii-sulfate | iron-ii-oxide + sulfur-trioxide | retort, red heat | `sulfate-thermal-decomposition` |
| 2 | condensation to oil of vitriol | sulfur-trioxide + water | sulfuric-acid | receiver | `hydrolysis` |

<a id="saltpetre-nitric"></a>

### nitric acid from saltpetre

`saltpetre-nitric` &middot; heavy-inorganic &middot; target: nitric acid `nitric-acid`

> aqua fortis by distillation with vitriol

**Primary feedstocks** (2)

- potassium nitrate `potassium-nitrate`
- sulfuric acid `sulfuric-acid`

**Intermediates** (0)

- *(none: a single-step route has no intermediate by definition)*

**Products and byproducts** (2)

- nitric acid `nitric-acid`
- potassium bisulfate `potassium-bisulfate`

| # | step | in | out | conditions | class |
|--:|---|---|---|---|---|
| 1 | displacement and distillation | potassium-nitrate + sulfuric-acid | nitric-acid + potassium-bisulfate | retort, red heat | `acid-displacement` |

<a id="aqua-regia"></a>

### aqua regia

`aqua-regia` &middot; heavy-inorganic &middot; target: nitrosyl chloride `nitrosyl-chloride`

> the gold solvent

**Primary feedstocks** (3)

- gold metal `gold`
- hydrogen chloride `hydrogen-chloride`
- nitric acid `nitric-acid`

**Intermediates** (1)

- dichlorine `chlorine`

**Products and byproducts** (3)

- chloroauric acid `chloroauric-acid`
- nitrosyl chloride `nitrosyl-chloride`
- water `water`

| # | step | in | out | conditions | class |
|--:|---|---|---|---|---|
| 1 | aqua regia formation | nitric-acid + hydrogen-chloride | nitrosyl-chloride + chlorine + water | 3:1 HCl:HNO3 | `halide-oxidation` |
| 2 | gold dissolution | gold + chlorine + hydrogen-chloride | chloroauric-acid | ambient | `oxidative-dissolution` |

<a id="vermilion-route"></a>

### vermilion from mercury and sulfur

`vermilion-route` &middot; pigments &middot; target: mercury(II) sulfide `mercury-sulfide`

> the alchemical red

**Primary feedstocks** (2)

- mercury `mercury`
- sulfur (S8 crown) `sulfur-s8`

**Intermediates** (0)

- *(none: a single-step route has no intermediate by definition)*

**Products and byproducts** (1)

- mercury(II) sulfide `mercury-sulfide`

| # | step | in | out | conditions | class |
|--:|---|---|---|---|---|
| 1 | mercury sulfide formation | mercury + sulfur-s8 | mercury-sulfide | trituration then sublimation | `direct-combination` |

## 1700s

<a id="lead-chamber"></a>

### lead chamber sulfuric acid

`lead-chamber` &middot; heavy-inorganic &middot; target: sulfuric acid `sulfuric-acid`

> the NOx carrier cycle; already implemented in reactions/library

**Primary feedstocks** (2)

- dioxygen `oxygen`
- sulfur (S8 crown) `sulfur-s8`

**Intermediates** (5)

- nitric oxide `nitric-oxide`
- nitrogen dioxide `nitrogen-dioxide`
- sulfur dioxide `sulfur-dioxide`
- sulfuric acid `sulfuric-acid`
- water `water`

**Products and byproducts** (1)

- nitrosylsulfuric acid `nitrosylsulfuric-acid`

| # | step | in | out | conditions | class |
|--:|---|---|---|---|---|
| 1 | sulfur combustion | sulfur-s8 + oxygen | sulfur-dioxide | burner, 600-1200 K | `combustion` |
| 2 | SO2 oxidation by NO2 | sulfur-dioxide + nitrogen-dioxide + water | sulfuric-acid + nitric-oxide | chamber, 330-370 K | `redox-oxygen-transfer` |
| 3 | carrier regeneration | nitric-oxide + oxygen | nitrogen-dioxide | chamber, cold favoured | `gas-phase-oxidation` |
| 4 | chamber crystal formation | nitrogen-dioxide + sulfur-dioxide + sulfuric-acid | nitrosylsulfuric-acid + water | water-starved chamber | `nitrosation` |

<a id="leblanc-process"></a>

### Leblanc soda process

`leblanc-process` &middot; heavy-inorganic &middot; target: sodium carbonate `sodium-carbonate`

> salt cake, black ash, galligu waste

**Primary feedstocks** (3)

- graphite `carbon-graphite`
- sodium chloride `sodium-chloride`
- sulfuric acid `sulfuric-acid`

**Intermediates** (4)

- calcium carbonate `calcium-carbonate`
- calcium sulfide `calcium-sulfide`
- carbon dioxide `carbon-dioxide`
- sodium sulfate `sodium-sulfate`

**Products and byproducts** (2)

- hydrogen chloride `hydrogen-chloride`
- hydrogen sulfide `hydrogen-sulfide`

**Catalysts** (both sides of one step, net stoichiometry zero)

- sodium carbonate `sodium-carbonate`
- water `water`

| # | step | in | out | conditions | class |
|--:|---|---|---|---|---|
| 1 | salt cake | sodium-chloride + sulfuric-acid | sodium-sulfate + hydrogen-chloride | 1100 K | `salt-metathesis` |
| 2 | black ash | sodium-sulfate + carbon-graphite + calcium-carbonate | sodium-carbonate + calcium-sulfide + carbon-dioxide | reverberatory furnace | `carbothermic-reduction` |
| 3 | lixiviation | sodium-carbonate + water | sodium-carbonate + water | leaching, crystallisation | `dissolution` |
| 4 | galligu waste weathering | calcium-sulfide + water + carbon-dioxide | calcium-carbonate + hydrogen-sulfide | tip, open air | `hydrolysis` |

<a id="white-phosphorus"></a>

### white phosphorus from bone ash

`white-phosphorus` &middot; heavy-inorganic &middot; target: white phosphorus (P4) `phosphorus-white`

> electric furnace / retort reduction

**Primary feedstocks** (3)

- tricalcium phosphate `calcium-phosphate`
- graphite `carbon-graphite`
- silicon dioxide `silicon-dioxide`

**Intermediates** (0)

- *(none: a single-step route has no intermediate by definition)*

**Products and byproducts** (3)

- calcium silicate `calcium-silicate`
- carbon monoxide `carbon-monoxide`
- white phosphorus (P4) `phosphorus-white`

| # | step | in | out | conditions | class |
|--:|---|---|---|---|---|
| 1 | carbothermic reduction | calcium-phosphate + silicon-dioxide + carbon-graphite | phosphorus-white + carbon-monoxide + calcium-silicate | electric furnace, 1700 K | `carbothermic-reduction` |

<a id="zinc-smelting"></a>

### zinc retort smelting

`zinc-smelting` &middot; metallurgy &middot; target: zinc metal `zinc`

> sphalerite roast then carbon reduction

**Primary feedstocks** (3)

- graphite `carbon-graphite`
- dioxygen `oxygen`
- zinc sulfide `zinc-sulfide`

**Intermediates** (1)

- zinc oxide `zinc-oxide`

**Products and byproducts** (3)

- carbon monoxide `carbon-monoxide`
- sulfur dioxide `sulfur-dioxide`
- zinc metal `zinc`

| # | step | in | out | conditions | class |
|--:|---|---|---|---|---|
| 1 | sphalerite roasting | zinc-sulfide + oxygen | zinc-oxide + sulfur-dioxide | roaster | `roasting` |
| 2 | retort reduction | zinc-oxide + carbon-graphite | zinc + carbon-monoxide | retort, 1400 K | `carbothermic-reduction` |

<a id="prussian-blue-route"></a>

### Prussian blue

`prussian-blue-route` &middot; pigments &middot; target: Prussian blue `prussian-blue`

> the first modern synthetic pigment

**Primary feedstocks** (3)

- iron metal `iron`
- iron(III) sulfate `iron-iii-sulfate`
- potassium carbonate `potassium-carbonate`

**Intermediates** (1)

- potassium ferrocyanide `potassium-ferrocyanide`

**Products and byproducts** (3)

- carbon dioxide `carbon-dioxide`
- potassium sulfate `potassium-sulfate`
- Prussian blue `prussian-blue`

| # | step | in | out | conditions | class |
|--:|---|---|---|---|---|
| 1 | ferrocyanide from potash and blood | potassium-carbonate + iron | potassium-ferrocyanide + carbon-dioxide | calcination with animal matter | `pyrolytic-synthesis` |
| 2 | pigment precipitation | potassium-ferrocyanide + iron-iii-sulfate | prussian-blue + potassium-sulfate | aqueous, ambient | `precipitation-metathesis` |

<a id="wood-distillation"></a>

### destructive distillation of wood

`wood-distillation` &middot; syngas &middot; target: methanol `methanol`

> pyroligneous acid

**Primary feedstocks** (1)

- cellulose repeat unit `cellulose-unit`

**Intermediates** (0)

- *(none: a single-step route has no intermediate by definition)*

**Products and byproducts** (5)

- ethanoic acid `acetic-acid`
- propanone `acetone`
- graphite `carbon-graphite`
- methanol `methanol`
- water `water`

| # | step | in | out | conditions | class |
|--:|---|---|---|---|---|
| 1 | pyrolysis of wood | cellulose-unit | methanol + acetic-acid + acetone + carbon-graphite + water | retort, 700 K, no air | `pyrolysis` |

## 1800s

<a id="contact-process"></a>

### contact process sulfuric acid

`contact-process` &middot; heavy-inorganic &middot; target: sulfuric acid `sulfuric-acid`

> V2O5 catalysed SO2 oxidation

**Primary feedstocks** (3)

- dioxygen `oxygen`
- sulfur (S8 crown) `sulfur-s8`
- water `water`

**Intermediates** (4)

- disulfuric acid (oleum) `disulfuric-acid`
- sulfur dioxide `sulfur-dioxide`
- sulfur trioxide `sulfur-trioxide`
- sulfuric acid `sulfuric-acid`

**Products and byproducts** (0)

- *(none)*

**Catalysts** (both sides of one step, net stoichiometry zero)

- vanadium(V) oxide `vanadium-pentoxide`

| # | step | in | out | conditions | class |
|--:|---|---|---|---|---|
| 1 | sulfur combustion | sulfur-s8 + oxygen | sulfur-dioxide | burner | `combustion` |
| 2 | catalytic SO2 oxidation | sulfur-dioxide + oxygen + vanadium-pentoxide | sulfur-trioxide + vanadium-pentoxide | 700-900 K, V2O5 | `catalytic-gas-oxidation` |
| 3 | absorption into oleum | sulfur-trioxide + sulfuric-acid | disulfuric-acid | absorber, 98% acid | `acid-anhydride-absorption` |
| 4 | oleum dilution | disulfuric-acid + water | sulfuric-acid | dilution | `hydrolysis` |

<a id="pyrite-roasting"></a>

### pyrite roasting to SO2

`pyrite-roasting` &middot; heavy-inorganic &middot; target: sulfur dioxide `sulfur-dioxide`

> the sulfur source before Frasch

**Primary feedstocks** (2)

- pyrite `iron-disulfide`
- dioxygen `oxygen`

**Intermediates** (0)

- *(none: a single-step route has no intermediate by definition)*

**Products and byproducts** (2)

- iron(III) oxide `iron-iii-oxide`
- sulfur dioxide `sulfur-dioxide`

| # | step | in | out | conditions | class |
|--:|---|---|---|---|---|
| 1 | pyrite roasting | iron-disulfide + oxygen | iron-iii-oxide + sulfur-dioxide | roaster, 1100 K | `roasting` |

<a id="solvay-process"></a>

### Solvay ammonia-soda process

`solvay-process` &middot; heavy-inorganic &middot; target: sodium carbonate `sodium-carbonate`

> ammonia recycled, calcium chloride wasted

**Primary feedstocks** (1)

- calcium carbonate `calcium-carbonate`

**Intermediates** (8)

- ammonia `ammonia`
- ammonium chloride `ammonium-chloride`
- ammonia solution `ammonium-hydroxide`
- calcium hydroxide `calcium-hydroxide`
- calcium oxide `calcium-oxide`
- carbon dioxide `carbon-dioxide`
- sodium bicarbonate `sodium-bicarbonate`
- water `water`

**Products and byproducts** (2)

- calcium chloride `calcium-chloride`
- sodium carbonate `sodium-carbonate`

**Catalysts** (both sides of one step, net stoichiometry zero)

- sodium chloride `sodium-chloride`

| # | step | in | out | conditions | class |
|--:|---|---|---|---|---|
| 1 | brine ammoniation | sodium-chloride + ammonia + water | sodium-chloride + ammonium-hydroxide | absorber | `carbonate-equilibrium` |
| 2 | carbonation | ammonium-hydroxide + carbon-dioxide + sodium-chloride | sodium-bicarbonate + ammonium-chloride | Solvay tower, cold | `precipitation-metathesis` |
| 3 | bicarbonate calcination | sodium-bicarbonate | sodium-carbonate + carbon-dioxide + water | calciner, 450 K | `bicarbonate-thermal-decomposition` |
| 4 | ammonia recovery | ammonium-chloride + calcium-hydroxide | ammonia + calcium-chloride + water | still | `proton-transfer` |
| 5 | lime kiln for CO2 | calcium-carbonate | calcium-oxide + carbon-dioxide | kiln, 1200 K | `calcination` |
| 6 | lime slaking | calcium-oxide + water | calcium-hydroxide | slaker | `lime-slaking` |

<a id="chloralkali"></a>

### chloralkali electrolysis

`chloralkali` &middot; heavy-inorganic &middot; target: sodium hydroxide `sodium-hydroxide`

> co-produces chlorine and hydrogen

**Primary feedstocks** (2)

- sodium chloride `sodium-chloride`
- water `water`

**Intermediates** (0)

- *(none: a single-step route has no intermediate by definition)*

**Products and byproducts** (3)

- dichlorine `chlorine`
- hydrogen `hydrogen`
- sodium hydroxide `sodium-hydroxide`

| # | step | in | out | conditions | class |
|--:|---|---|---|---|---|
| 1 | brine electrolysis | sodium-chloride + water | sodium-hydroxide + chlorine + hydrogen | membrane cell, 3 V | `electrolysis` |

<a id="deacon-process"></a>

### Deacon chlorine process

`deacon-process` &middot; heavy-inorganic &middot; target: dichlorine `chlorine`

> HCl reoxidation over copper

**Primary feedstocks** (2)

- hydrogen chloride `hydrogen-chloride`
- dioxygen `oxygen`

**Intermediates** (0)

- *(none: a single-step route has no intermediate by definition)*

**Products and byproducts** (2)

- dichlorine `chlorine`
- water `water`

**Catalysts** (both sides of one step, net stoichiometry zero)

- copper(II) oxide `copper-ii-oxide`

| # | step | in | out | conditions | class |
|--:|---|---|---|---|---|
| 1 | HCl reoxidation | hydrogen-chloride + oxygen + copper-ii-oxide | chlorine + water + copper-ii-oxide | 700 K, CuCl2 | `catalytic-gas-oxidation` |

<a id="weldon-chlorine"></a>

### Weldon chlorine from pyrolusite

`weldon-chlorine` &middot; heavy-inorganic &middot; target: dichlorine `chlorine`

> MnO2 plus HCl

**Primary feedstocks** (2)

- hydrogen chloride `hydrogen-chloride`
- manganese dioxide `manganese-dioxide`

**Intermediates** (0)

- *(none: a single-step route has no intermediate by definition)*

**Products and byproducts** (3)

- dichlorine `chlorine`
- manganese(II) chloride `manganese-ii-chloride`
- water `water`

| # | step | in | out | conditions | class |
|--:|---|---|---|---|---|
| 1 | pyrolusite oxidation of HCl | manganese-dioxide + hydrogen-chloride | chlorine + water + manganese-ii-chloride | warm | `halide-oxidation` |

<a id="bleaching-powder"></a>

### bleaching powder manufacture

`bleaching-powder` &middot; heavy-inorganic &middot; target: calcium hypochlorite `calcium-hypochlorite`

> Tennant chlorinated lime

**Primary feedstocks** (2)

- calcium hydroxide `calcium-hydroxide`
- dichlorine `chlorine`

**Intermediates** (0)

- *(none: a single-step route has no intermediate by definition)*

**Products and byproducts** (3)

- calcium chloride `calcium-chloride`
- calcium hypochlorite `calcium-hypochlorite`
- water `water`

| # | step | in | out | conditions | class |
|--:|---|---|---|---|---|
| 1 | chlorination of lime | calcium-hydroxide + chlorine | calcium-hypochlorite + calcium-chloride + water | ambient | `disproportionation` |

<a id="superphosphate"></a>

### superphosphate fertiliser

`superphosphate` &middot; agriculture &middot; target: monocalcium phosphate `monocalcium-phosphate`

> Lawes patent

**Primary feedstocks** (2)

- tricalcium phosphate `calcium-phosphate`
- sulfuric acid `sulfuric-acid`

**Intermediates** (0)

- *(none: a single-step route has no intermediate by definition)*

**Products and byproducts** (2)

- calcium sulfate `calcium-sulfate`
- monocalcium phosphate `monocalcium-phosphate`

| # | step | in | out | conditions | class |
|--:|---|---|---|---|---|
| 1 | rock acidulation | calcium-phosphate + sulfuric-acid | monocalcium-phosphate + calcium-sulfate | den, ambient | `acid-displacement-precipitating` |

<a id="match-chemistry"></a>

### strike-anywhere match head

`match-chemistry` &middot; consumer &middot; target: phosphorus pentoxide `phosphorus-pentoxide`

> the phosphorus and chlorate mix

**Primary feedstocks** (2)

- white phosphorus (P4) `phosphorus-white`
- potassium chlorate `potassium-chlorate`

**Intermediates** (0)

- *(none: a single-step route has no intermediate by definition)*

**Products and byproducts** (2)

- phosphorus pentoxide `phosphorus-pentoxide`
- potassium chloride `potassium-chloride`

| # | step | in | out | conditions | class |
|--:|---|---|---|---|---|
| 1 | match head ignition | potassium-chlorate + phosphorus-white | phosphorus-pentoxide + potassium-chloride | friction | `combustion` |

<a id="bayer-process"></a>

### Bayer alumina process

`bayer-process` &middot; metallurgy &middot; target: aluminium oxide `aluminium-oxide`

> bauxite digestion in caustic

**Primary feedstocks** (0)

- *(none: every species is made inside the route)*

**Intermediates** (5)

- aluminium hydroxide `aluminium-hydroxide`
- aluminium oxide `aluminium-oxide`
- sodium aluminate `sodium-aluminate`
- sodium hydroxide `sodium-hydroxide`
- water `water`

**Products and byproducts** (0)

- *(none)*

| # | step | in | out | conditions | class |
|--:|---|---|---|---|---|
| 1 | bauxite digestion | aluminium-oxide + sodium-hydroxide + water | sodium-aluminate | 500 K, 5 bar | `amphoteric-dissolution` |
| 2 | precipitation of hydroxide | sodium-aluminate + water | aluminium-hydroxide + sodium-hydroxide | seeded, cooling | `precipitation` |
| 3 | calcination to alumina | aluminium-hydroxide | aluminium-oxide + water | 1300 K | `calcination` |

<a id="hall-heroult"></a>

### Hall-Heroult aluminium

`hall-heroult` &middot; metallurgy &middot; target: aluminium metal `aluminium`

> cryolite melt electrolysis

**Primary feedstocks** (2)

- aluminium oxide `aluminium-oxide`
- graphite `carbon-graphite`

**Intermediates** (0)

- *(none: a single-step route has no intermediate by definition)*

**Products and byproducts** (2)

- aluminium metal `aluminium`
- carbon dioxide `carbon-dioxide`

**Catalysts** (both sides of one step, net stoichiometry zero)

- cryolite `cryolite`

| # | step | in | out | conditions | class |
|--:|---|---|---|---|---|
| 1 | alumina electrolysis | aluminium-oxide + carbon-graphite + cryolite | aluminium + carbon-dioxide + cryolite | 1250 K, cryolite melt | `electrolysis` |

<a id="thermite"></a>

### thermite reaction

`thermite` &middot; metallurgy &middot; target: iron metal `iron`

> aluminothermic reduction

**Primary feedstocks** (2)

- aluminium metal `aluminium`
- iron(III) oxide `iron-iii-oxide`

**Intermediates** (0)

- *(none: a single-step route has no intermediate by definition)*

**Products and byproducts** (2)

- aluminium oxide `aluminium-oxide`
- iron metal `iron`

| # | step | in | out | conditions | class |
|--:|---|---|---|---|---|
| 1 | aluminothermic reduction | iron-iii-oxide + aluminium | iron + aluminium-oxide | ignition, 3000 K | `metallothermic-reduction` |

<a id="castner-kellner"></a>

### Castner-Kellner mercury cell

`castner-kellner` &middot; heavy-inorganic &middot; target: sodium hydroxide `sodium-hydroxide`

> amalgam route to caustic

**Primary feedstocks** (2)

- sodium chloride `sodium-chloride`
- water `water`

**Intermediates** (2)

- mercury `mercury`
- *sodium-amalgam-marker* (no molecular graph)

**Products and byproducts** (3)

- dichlorine `chlorine`
- hydrogen `hydrogen`
- sodium hydroxide `sodium-hydroxide`

| # | step | in | out | conditions | class |
|--:|---|---|---|---|---|
| 1 | amalgam formation | sodium-chloride + mercury | sodium-amalgam-marker + chlorine | mercury cathode | `electrolysis` |
| 2 | amalgam decomposition | sodium-amalgam-marker + water | sodium-hydroxide + hydrogen + mercury | denuder | `hydrolysis` |

<a id="nitroglycerin-route"></a>

### nitroglycerin and dynamite

`nitroglycerin-route` &middot; energetics &middot; target: glyceryl trinitrate `nitroglycerin`

> Sobrero and Nobel

**Primary feedstocks** (2)

- 1,2,3-propanetriol `glycerol`
- nitric acid `nitric-acid`

**Intermediates** (0)

- *(none: a single-step route has no intermediate by definition)*

**Products and byproducts** (1)

- water `water`

**Catalysts** (both sides of one step, net stoichiometry zero)

- glyceryl trinitrate `nitroglycerin`
- sulfuric acid `sulfuric-acid`

| # | step | in | out | conditions | class |
|--:|---|---|---|---|---|
| 1 | glycerol nitration | glycerol + nitric-acid + sulfuric-acid | nitroglycerin + water + sulfuric-acid | 283 K, mixed acid, stirred | `esterification-nitration` |
| 2 | absorption into kieselguhr | nitroglycerin | nitroglycerin | Nobel dynamite | `formulation` |

<a id="guncotton"></a>

### nitrocellulose / guncotton

`guncotton` &middot; energetics &middot; target: nitrocellulose repeat unit `nitrocellulose-unit`

> Schoenbein

**Primary feedstocks** (2)

- cellulose repeat unit `cellulose-unit`
- nitric acid `nitric-acid`

**Intermediates** (0)

- *(none: a single-step route has no intermediate by definition)*

**Products and byproducts** (2)

- nitrocellulose repeat unit `nitrocellulose-unit`
- water `water`

**Catalysts** (both sides of one step, net stoichiometry zero)

- sulfuric acid `sulfuric-acid`

| # | step | in | out | conditions | class |
|--:|---|---|---|---|---|
| 1 | cellulose nitration | cellulose-unit + nitric-acid + sulfuric-acid | nitrocellulose-unit + water + sulfuric-acid | 290 K, mixed acid | `esterification-nitration` |

<a id="picric-acid-route"></a>

### picric acid from phenol

`picric-acid-route` &middot; energetics &middot; target: 2,4,6-trinitrophenol `picric-acid`

> dye first, explosive later

**Primary feedstocks** (2)

- nitric acid `nitric-acid`
- phenol `phenol`

**Intermediates** (2)

- benzenesulfonic acid `benzenesulfonic-acid`
- sulfuric acid `sulfuric-acid`

**Products and byproducts** (2)

- 2,4,6-trinitrophenol `picric-acid`
- water `water`

| # | step | in | out | conditions | class |
|--:|---|---|---|---|---|
| 1 | phenol sulfonation | phenol + sulfuric-acid | benzenesulfonic-acid + water | 370 K, protects the ring | `electrophilic-aromatic-sulfonation` |
| 2 | nitration and desulfonation | benzenesulfonic-acid + nitric-acid | picric-acid + water + sulfuric-acid | 380 K | `ipso-nitrodesulfonation` |

<a id="mercury-fulminate-route"></a>

### mercury fulminate

`mercury-fulminate-route` &middot; energetics &middot; target: mercury fulminate `mercury-fulminate`

> the percussion cap

**Primary feedstocks** (3)

- ethanol `ethanol`
- mercury `mercury`
- nitric acid `nitric-acid`

**Intermediates** (0)

- *(none: a single-step route has no intermediate by definition)*

**Products and byproducts** (3)

- mercury fulminate `mercury-fulminate`
- nitric oxide `nitric-oxide`
- water `water`

| # | step | in | out | conditions | class |
|--:|---|---|---|---|---|
| 1 | fulminate formation | mercury + nitric-acid + ethanol | mercury-fulminate + water + nitric-oxide | Howard process | `oxidative-nitrosation` |

<a id="coal-tar-distillation"></a>

### coal tar fractionation

`coal-tar-distillation` &middot; aromatics &middot; target: benzene `benzene`

> the source of every early aromatic

**Primary feedstocks** (1)

- *coal-tar-marker* (no molecular graph)

**Intermediates** (0)

- *(none: a single-step route has no intermediate by definition)*

**Products and byproducts** (9)

- anthracene `anthracene`
- benzene `benzene`
- 9H-carbazole `carbazole`
- naphthalene `naphthalene`
- ortho-xylene `o-xylene`
- phenol `phenol`
- pyridine `pyridine`
- quinoline `quinoline`
- toluene `toluene`

| # | step | in | out | conditions | class |
|--:|---|---|---|---|---|
| 1 | tar fractionation | coal-tar-marker | benzene + toluene + o-xylene + phenol + naphthalene + anthracene + pyridine + quinoline + carbazole | fractional distillation | `separation` |

<a id="coal-gas"></a>

### coal gas and coke

`coal-gas` &middot; aromatics &middot; target: *coal-tar-marker* (no molecular graph)

> destructive distillation of coal

**Primary feedstocks** (1)

- *coal-marker* (no molecular graph)

**Intermediates** (0)

- *(none: a single-step route has no intermediate by definition)*

**Products and byproducts** (6)

- ammonia `ammonia`
- graphite `carbon-graphite`
- carbon monoxide `carbon-monoxide`
- *coal-tar-marker* (no molecular graph)
- hydrogen `hydrogen`
- methane `methane`

| # | step | in | out | conditions | class |
|--:|---|---|---|---|---|
| 1 | destructive distillation | coal-marker | coal-tar-marker + methane + hydrogen + carbon-monoxide + ammonia + carbon-graphite | retort, 1300 K, no air | `pyrolysis` |

<a id="benzene-nitration"></a>

### nitration of benzene

`benzene-nitration` &middot; aromatics &middot; target: nitrobenzene `nitrobenzene`

> mixed acid, nitronium ion

**Primary feedstocks** (2)

- benzene `benzene`
- nitric acid `nitric-acid`

**Intermediates** (4)

- benzenium ion (sigma complex) `arenium-benzene`
- bisulfate ion `bisulfate-ion`
- nitronium ion `nitronium`
- sulfuric acid `sulfuric-acid`

**Products and byproducts** (2)

- nitrobenzene `nitrobenzene`
- water `water`

| # | step | in | out | conditions | class |
|--:|---|---|---|---|---|
| 1 | nitronium generation | nitric-acid + sulfuric-acid | nitronium + bisulfate-ion + water | mixed acid | `nitronium-generation` |
| 2 | electrophilic attack | benzene + nitronium | arenium-benzene | 330 K | `electrophilic-aromatic-substitution` |
| 3 | proton loss | arenium-benzene + bisulfate-ion | nitrobenzene + sulfuric-acid | fast | `arenium-deprotonation` |

<a id="aniline-route"></a>

### aniline from nitrobenzene

`aniline-route` &middot; aromatics &middot; target: phenylamine `aniline`

> Bechamp then catalytic hydrogenation

**Primary feedstocks** (4)

- hydrogen `hydrogen`
- hydrogen chloride `hydrogen-chloride`
- iron metal `iron`
- nitrobenzene `nitrobenzene`

**Intermediates** (0)

- *(none: a single-step route has no intermediate by definition)*

**Products and byproducts** (3)

- phenylamine `aniline`
- iron(III) oxide `iron-iii-oxide`
- water `water`

**Catalysts** (both sides of one step, net stoichiometry zero)

- copper metal `copper`

| # | step | in | out | conditions | class |
|--:|---|---|---|---|---|
| 1 | Bechamp reduction | nitrobenzene + iron + hydrogen-chloride | aniline + iron-iii-oxide + water | boiling, iron filings | `dissolving-metal-reduction` |
| 2 | catalytic hydrogenation | nitrobenzene + hydrogen + copper | aniline + water + copper | 470 K, Cu on silica | `nitro-hydrogenation` |

<a id="mauveine-route"></a>

### Perkin mauve

`mauveine-route` &middot; dyes &middot; target: mauveine A `mauveine-a`

> the accident that started the dye industry

**Primary feedstocks** (4)

- phenylamine `aniline`
- 2-methylaniline `o-toluidine`
- 4-methylaniline `p-toluidine`
- potassium dichromate `potassium-dichromate`

**Intermediates** (0)

- *(none: a single-step route has no intermediate by definition)*

**Products and byproducts** (2)

- mauveine A `mauveine-a`
- water `water`

| # | step | in | out | conditions | class |
|--:|---|---|---|---|---|
| 1 | oxidation of crude aniline | aniline + o-toluidine + p-toluidine + potassium-dichromate | mauveine-a + water | ambient, aqueous | `oxidative-coupling` |

<a id="alizarin-route"></a>

### synthetic alizarin

`alizarin-route` &middot; dyes &middot; target: 1,2-dihydroxyanthraquinone `alizarin`

> anthraquinone sulfonation and alkali fusion

**Primary feedstocks** (5)

- anthracene `anthracene`
- disulfuric acid (oleum) `disulfuric-acid`
- potassium dichromate `potassium-dichromate`
- potassium nitrate `potassium-nitrate`
- sodium hydroxide `sodium-hydroxide`

**Intermediates** (2)

- 9,10-anthraquinone `anthraquinone`
- anthraquinone-2-sulfonic acid `anthraquinone-2-sulfonic-acid`

**Products and byproducts** (3)

- 1,2-dihydroxyanthraquinone `alizarin`
- sodium sulfite `sodium-sulfite`
- water `water`

| # | step | in | out | conditions | class |
|--:|---|---|---|---|---|
| 1 | anthracene oxidation | anthracene + potassium-dichromate | anthraquinone + water | sulfuric acid, warm | `arene-oxidation-to-quinone` |
| 2 | sulfonation | anthraquinone + disulfuric-acid | anthraquinone-2-sulfonic-acid + water | oleum, 420 K | `electrophilic-aromatic-sulfonation` |
| 3 | alkali fusion | anthraquinone-2-sulfonic-acid + sodium-hydroxide + potassium-nitrate | alizarin + sodium-sulfite | fusion, 470 K | `alkali-fusion` |

<a id="indigo-baeyer-drewson"></a>

### Baeyer-Drewson indigo

`indigo-baeyer-drewson` &middot; dyes &middot; target: indigo `indigo`

> from 2-nitrobenzaldehyde and acetone

**Primary feedstocks** (5)

- propanone `acetone`
- manganese dioxide `manganese-dioxide`
- nitric acid `nitric-acid`
- sodium hydroxide `sodium-hydroxide`
- toluene `toluene`

**Intermediates** (2)

- 2-nitrobenzaldehyde `2-nitrobenzaldehyde`
- 2-nitrotoluene `2-nitrotoluene`

**Products and byproducts** (3)

- ethanoic acid `acetic-acid`
- indigo `indigo`
- water `water`

**Catalysts** (both sides of one step, net stoichiometry zero)

- sulfuric acid `sulfuric-acid`

| # | step | in | out | conditions | class |
|--:|---|---|---|---|---|
| 1 | toluene nitration to ortho | toluene + nitric-acid + sulfuric-acid | 2-nitrotoluene + water + sulfuric-acid | mixed acid | `electrophilic-aromatic-nitration` |
| 2 | side-chain oxidation | 2-nitrotoluene + manganese-dioxide | 2-nitrobenzaldehyde + water | oxidation | `side-chain-oxidation` |
| 3 | aldol and cyclisation | 2-nitrobenzaldehyde + acetone + sodium-hydroxide | indigo + acetic-acid + water | cold dilute base | `aldol-cyclisation` |

<a id="indigo-heumann"></a>

### Heumann-Pfleger indigo

`indigo-heumann` &middot; dyes &middot; target: indigo `indigo`

> the industrial aniline route

**Primary feedstocks** (5)

- phenylamine `aniline`
- chloroacetic acid `chloroacetic-acid`
- dioxygen `oxygen`
- sodium amide `sodium-amide`
- sodium hydroxide `sodium-hydroxide`

**Intermediates** (2)

- indoxyl `indoxyl`
- N-phenylglycine `n-phenylglycine`

**Products and byproducts** (3)

- hydrogen chloride `hydrogen-chloride`
- indigo `indigo`
- water `water`

| # | step | in | out | conditions | class |
|--:|---|---|---|---|---|
| 1 | N-alkylation of aniline | aniline + chloroacetic-acid | n-phenylglycine + hydrogen-chloride | 370 K | `n-alkylation` |
| 2 | alkali fusion to indoxyl | n-phenylglycine + sodium-hydroxide + sodium-amide | indoxyl + water | 470 K, sodamide | `alkali-fusion` |
| 3 | air oxidation to indigo | indoxyl + oxygen | indigo + water | air blown | `oxidative-dimerisation` |

<a id="azo-dye-coupling"></a>

### diazotisation and azo coupling

`azo-dye-coupling` &middot; dyes &middot; target: methyl orange `methyl-orange`

> the general azo dye route

**Primary feedstocks** (3)

- N,N-dimethylaniline `n,n-dimethylaniline`
- sodium nitrite `sodium-nitrite`
- 4-aminobenzenesulfonic acid `sulfanilic-acid`

**Intermediates** (2)

- benzenediazonium chloride `benzenediazonium-chloride`
- hydrogen chloride `hydrogen-chloride`

**Products and byproducts** (3)

- methyl orange `methyl-orange`
- sodium chloride `sodium-chloride`
- water `water`

| # | step | in | out | conditions | class |
|--:|---|---|---|---|---|
| 1 | diazotisation | sulfanilic-acid + sodium-nitrite + hydrogen-chloride | benzenediazonium-chloride + water + sodium-chloride | 275-278 K, ice bath | `diazotisation` |
| 2 | azo coupling | benzenediazonium-chloride + n,n-dimethylaniline | methyl-orange + hydrogen-chloride | pH 5-9, cold | `azo-coupling` |

<a id="triarylmethane-dyes"></a>

### malachite green

`triarylmethane-dyes` &middot; dyes &middot; target: malachite green `malachite-green`

> benzaldehyde plus dimethylaniline

**Primary feedstocks** (4)

- benzaldehyde `benzaldehyde`
- hydrogen chloride `hydrogen-chloride`
- lead(IV) oxide `lead-iv-oxide`
- N,N-dimethylaniline `n,n-dimethylaniline`

**Intermediates** (1)

- leucomalachite green `leucomalachite-green`

**Products and byproducts** (2)

- malachite green `malachite-green`
- water `water`

| # | step | in | out | conditions | class |
|--:|---|---|---|---|---|
| 1 | condensation | benzaldehyde + n,n-dimethylaniline + hydrogen-chloride | leucomalachite-green + water | acid, 370 K | `friedel-crafts-hydroxyalkylation` |
| 2 | oxidation to the dye | leucomalachite-green + lead-iv-oxide | malachite-green + water | oxidation | `leuco-dye-oxidation` |

<a id="chrome-yellow-route"></a>

### chrome yellow

`chrome-yellow-route` &middot; pigments &middot; target: lead chromate `chrome-yellow`

> lead nitrate plus chromate

**Primary feedstocks** (2)

- lead(II) acetate `lead-acetate`
- potassium chromate `potassium-chromate`

**Intermediates** (0)

- *(none: a single-step route has no intermediate by definition)*

**Products and byproducts** (2)

- lead chromate `chrome-yellow`
- potassium acetate `potassium-acetate`

| # | step | in | out | conditions | class |
|--:|---|---|---|---|---|
| 1 | precipitation | lead-acetate + potassium-chromate | chrome-yellow + potassium-acetate | aqueous | `precipitation-metathesis` |

<a id="phenol-sulfonation"></a>

### benzenesulfonate alkali fusion

`phenol-sulfonation` &middot; petrochemical &middot; target: phenol `phenol`

> the first industrial phenol

**Primary feedstocks** (3)

- benzene `benzene`
- sodium hydroxide `sodium-hydroxide`
- sulfuric acid `sulfuric-acid`

**Intermediates** (2)

- benzenesulfonic acid `benzenesulfonic-acid`
- sodium phenoxide `sodium-phenoxide`

**Products and byproducts** (4)

- phenol `phenol`
- sodium bisulfate `sodium-bisulfate`
- sodium sulfite `sodium-sulfite`
- water `water`

| # | step | in | out | conditions | class |
|--:|---|---|---|---|---|
| 1 | benzene sulfonation | benzene + sulfuric-acid | benzenesulfonic-acid + water | 420 K | `electrophilic-aromatic-sulfonation` |
| 2 | alkali fusion | benzenesulfonic-acid + sodium-hydroxide | sodium-phenoxide + sodium-sulfite + water | 620 K, molten caustic | `alkali-fusion` |
| 3 | acidification | sodium-phenoxide + sulfuric-acid | phenol + sodium-bisulfate | ambient | `proton-transfer` |

<a id="salicylic-kolbe"></a>

### Kolbe-Schmitt salicylic acid

`salicylic-kolbe` &middot; pharma &middot; target: 2-hydroxybenzoic acid `salicylic-acid`

> carboxylation of sodium phenoxide

**Primary feedstocks** (4)

- carbon dioxide `carbon-dioxide`
- phenol `phenol`
- sodium hydroxide `sodium-hydroxide`
- sulfuric acid `sulfuric-acid`

**Intermediates** (2)

- sodium phenoxide `sodium-phenoxide`
- sodium salicylate `sodium-salicylate`

**Products and byproducts** (3)

- 2-hydroxybenzoic acid `salicylic-acid`
- sodium bisulfate `sodium-bisulfate`
- water `water`

| # | step | in | out | conditions | class |
|--:|---|---|---|---|---|
| 1 | phenoxide formation | phenol + sodium-hydroxide | sodium-phenoxide + water | dried thoroughly | `proton-transfer` |
| 2 | carboxylation | sodium-phenoxide + carbon-dioxide | sodium-salicylate | 400 K, 100 bar CO2 | `kolbe-schmitt-carboxylation` |
| 3 | acidification | sodium-salicylate + sulfuric-acid | salicylic-acid + sodium-bisulfate | ambient | `proton-transfer` |

<a id="aspirin-route"></a>

### aspirin

`aspirin-route` &middot; pharma &middot; target: acetylsalicylic acid `aspirin`

> acetylation with acetic anhydride

**Primary feedstocks** (3)

- acetic anhydride `acetic-anhydride`
- 2-hydroxybenzoic acid `salicylic-acid`
- water `water`

**Intermediates** (0)

- *(none: a single-step route has no intermediate by definition)*

**Products and byproducts** (1)

- ethanoic acid `acetic-acid`

**Catalysts** (both sides of one step, net stoichiometry zero)

- acetylsalicylic acid `aspirin`
- sulfuric acid `sulfuric-acid`

| # | step | in | out | conditions | class |
|--:|---|---|---|---|---|
| 1 | acetylation | salicylic-acid + acetic-anhydride + sulfuric-acid | aspirin + acetic-acid + sulfuric-acid | 350 K, catalytic acid | `acylation-esterification` |
| 2 | crystallisation | aspirin + water | aspirin | cool to 273 K, recrystallise | `crystallisation` |

<a id="phenacetin-route"></a>

### phenacetin

`phenacetin-route` &middot; pharma &middot; target: phenacetin `phenacetin`

> Williamson ether then acetylation

**Primary feedstocks** (5)

- para-nitrophenol `4-nitrophenol`
- acetic anhydride `acetic-anhydride`
- bromoethane `bromoethane`
- hydrogen `hydrogen`
- sodium hydroxide `sodium-hydroxide`

**Intermediates** (2)

- 4-nitrophenetole `4-nitrophenetole`
- 4-ethoxyaniline `p-phenetidine`

**Products and byproducts** (4)

- ethanoic acid `acetic-acid`
- phenacetin `phenacetin`
- sodium bromide `sodium-bromide`
- water `water`

**Catalysts** (both sides of one step, net stoichiometry zero)

- nickel metal `nickel`

| # | step | in | out | conditions | class |
|--:|---|---|---|---|---|
| 1 | Williamson etherification | 4-nitrophenol + sodium-hydroxide + bromoethane | 4-nitrophenetole + sodium-bromide + water | reflux in ethanol | `williamson-ether-synthesis` |
| 2 | nitro reduction | 4-nitrophenetole + hydrogen + nickel | p-phenetidine + water + nickel | catalytic hydrogenation | `nitro-hydrogenation` |
| 3 | acetylation | p-phenetidine + acetic-anhydride | phenacetin + acetic-acid | 360 K | `n-acylation` |

<a id="salicin-hydrolysis"></a>

### salicin to salicylic acid

`salicin-hydrolysis` &middot; pharma &middot; target: 2-hydroxybenzoic acid `salicylic-acid`

> the willow-bark route

**Primary feedstocks** (2)

- dioxygen `oxygen`
- salicin `salicin`

**Intermediates** (4)

- hydrogen peroxide `hydrogen-peroxide`
- 2-hydroxybenzyl alcohol `salicyl-alcohol`
- 2-hydroxybenzaldehyde `salicylaldehyde`
- water `water`

**Products and byproducts** (2)

- D-glucose `glucose`
- 2-hydroxybenzoic acid `salicylic-acid`

| # | step | in | out | conditions | class |
|--:|---|---|---|---|---|
| 1 | glycoside hydrolysis | salicin + water | salicyl-alcohol + glucose | acid or emulsin | `glycoside-hydrolysis` |
| 2 | alcohol oxidation | salicyl-alcohol + oxygen | salicylaldehyde + hydrogen-peroxide | mild oxidation | `alcohol-oxidation` |
| 3 | aldehyde oxidation | salicylaldehyde + hydrogen-peroxide | salicylic-acid + water | oxidation | `aldehyde-oxidation` |

<a id="chloroform-route"></a>

### chloroform by the haloform reaction

`chloroform-route` &middot; fine-chemicals &middot; target: trichloromethane `chloroform`

> bleaching powder plus acetone or ethanol

**Primary feedstocks** (2)

- propanone `acetone`
- calcium hypochlorite `calcium-hypochlorite`

**Intermediates** (0)

- *(none: a single-step route has no intermediate by definition)*

**Products and byproducts** (3)

- calcium acetate `calcium-acetate`
- calcium hydroxide `calcium-hydroxide`
- trichloromethane `chloroform`

| # | step | in | out | conditions | class |
|--:|---|---|---|---|---|
| 1 | haloform reaction | acetone + calcium-hypochlorite | chloroform + calcium-acetate + calcium-hydroxide | 330 K, aqueous | `haloform` |

<a id="chloral-route"></a>

### chloral and chloral hydrate

`chloral-route` &middot; fine-chemicals &middot; target: chloral hydrate `chloral-hydrate`

> exhaustive chlorination of ethanol

**Primary feedstocks** (2)

- dichlorine `chlorine`
- ethanol `ethanol`

**Intermediates** (2)

- chloral `chloral`
- water `water`

**Products and byproducts** (2)

- chloral hydrate `chloral-hydrate`
- hydrogen chloride `hydrogen-chloride`

| # | step | in | out | conditions | class |
|--:|---|---|---|---|---|
| 1 | exhaustive chlorination | ethanol + chlorine | chloral + hydrogen-chloride + water | chlorine bubbled, days | `radical-halogenation` |
| 2 | hydrate formation | chloral + water | chloral-hydrate | crystallises | `carbonyl-hydration` |

<a id="water-gas-shift"></a>

### water gas shift

`water-gas-shift` &middot; syngas &middot; target: hydrogen `hydrogen`

> CO plus steam to CO2 and H2

**Primary feedstocks** (2)

- carbon monoxide `carbon-monoxide`
- water `water`

**Intermediates** (0)

- *(none: a single-step route has no intermediate by definition)*

**Products and byproducts** (2)

- carbon dioxide `carbon-dioxide`
- hydrogen `hydrogen`

**Catalysts** (both sides of one step, net stoichiometry zero)

- iron(III) oxide `iron-iii-oxide`

| # | step | in | out | conditions | class |
|--:|---|---|---|---|---|
| 1 | shift reaction | carbon-monoxide + water + iron-iii-oxide | carbon-dioxide + hydrogen + iron-iii-oxide | 620 K high-temp shift | `water-gas-shift` |

<a id="acetylene-acetaldehyde"></a>

### Kucherov acetylene hydration

`acetylene-acetaldehyde` &middot; petrochemical &middot; target: ethanal `acetaldehyde`

> mercury-catalysed, superseded by Wacker

**Primary feedstocks** (2)

- ethyne `acetylene`
- water `water`

**Intermediates** (0)

- *(none: a single-step route has no intermediate by definition)*

**Products and byproducts** (1)

- ethanal `acetaldehyde`

**Catalysts** (both sides of one step, net stoichiometry zero)

- mercury(II) ion `mercury-ii-ion`

| # | step | in | out | conditions | class |
|--:|---|---|---|---|---|
| 1 | mercury-catalysed hydration | acetylene + water + mercury-ii-ion | acetaldehyde + mercury-ii-ion | 370 K, HgSO4 in H2SO4 | `alkyne-hydration` |

<a id="calcium-carbide"></a>

### calcium carbide and acetylene

`calcium-carbide` &middot; petrochemical &middot; target: ethyne `acetylene`

> the carbide era feedstock

**Primary feedstocks** (3)

- calcium oxide `calcium-oxide`
- graphite `carbon-graphite`
- water `water`

**Intermediates** (1)

- calcium carbide `calcium-carbide`

**Products and byproducts** (3)

- ethyne `acetylene`
- calcium hydroxide `calcium-hydroxide`
- carbon monoxide `carbon-monoxide`

| # | step | in | out | conditions | class |
|--:|---|---|---|---|---|
| 1 | carbide furnace | calcium-oxide + carbon-graphite | calcium-carbide + carbon-monoxide | electric arc, 2300 K | `carbothermic-reduction` |
| 2 | carbide hydrolysis | calcium-carbide + water | acetylene + calcium-hydroxide | ambient, water drip | `hydrolysis` |

<a id="vulcanisation"></a>

### vulcanisation of rubber

`vulcanisation` &middot; polymers &middot; target: vulcanised rubber crosslink marker `vulcanised-rubber-marker`

> Goodyear; sulfur crosslinks

**Primary feedstocks** (2)

- polyisoprene repeat unit `polyisoprene-unit`
- sulfur (S8 crown) `sulfur-s8`

**Intermediates** (0)

- *(none: a single-step route has no intermediate by definition)*

**Products and byproducts** (1)

- vulcanised rubber crosslink marker `vulcanised-rubber-marker`

**Catalysts** (both sides of one step, net stoichiometry zero)

- zinc oxide `zinc-oxide`

| # | step | in | out | conditions | class |
|--:|---|---|---|---|---|
| 1 | sulfur crosslinking | polyisoprene-unit + sulfur-s8 + zinc-oxide | vulcanised-rubber-marker + zinc-oxide | 420 K, press, accelerator | `crosslinking` |

<a id="viscose-route"></a>

### viscose rayon

`viscose-route` &middot; polymers &middot; target: viscose xanthate intermediate marker `viscose-marker`

> cellulose xanthate then regeneration

**Primary feedstocks** (2)

- sodium hydroxide `sodium-hydroxide`
- sulfuric acid `sulfuric-acid`

**Intermediates** (4)

- *alkali-cellulose-marker* (no molecular graph)
- carbon disulfide `carbon-disulfide`
- cellulose repeat unit `cellulose-unit`
- viscose xanthate intermediate marker `viscose-marker`

**Products and byproducts** (2)

- sodium sulfate `sodium-sulfate`
- water `water`

| # | step | in | out | conditions | class |
|--:|---|---|---|---|---|
| 1 | alkali cellulose | cellulose-unit + sodium-hydroxide | alkali-cellulose-marker + water | steeping, 320 K | `polysaccharide-alkoxide` |
| 2 | xanthation | alkali-cellulose-marker + carbon-disulfide | viscose-marker | churn, 300 K | `xanthation` |
| 3 | spinning and regeneration | viscose-marker + sulfuric-acid | cellulose-unit + carbon-disulfide + sodium-sulfate | acid spin bath | `regeneration` |

<a id="celluloid-route"></a>

### celluloid

`celluloid-route` &middot; polymers &middot; target: celluloid marker (nitrocellulose plus camphor) `celluloid-marker`

> nitrocellulose plasticised with camphor

**Primary feedstocks** (2)

- camphor `camphor`
- nitrocellulose repeat unit `nitrocellulose-unit`

**Intermediates** (0)

- *(none: a single-step route has no intermediate by definition)*

**Products and byproducts** (1)

- celluloid marker (nitrocellulose plus camphor) `celluloid-marker`

**Catalysts** (both sides of one step, net stoichiometry zero)

- ethanol `ethanol`

| # | step | in | out | conditions | class |
|--:|---|---|---|---|---|
| 1 | plasticisation | nitrocellulose-unit + camphor + ethanol | celluloid-marker + ethanol | mill and press, 350 K | `formulation` |

<a id="starch-hydrolysis"></a>

### starch to glucose syrup

`starch-hydrolysis` &middot; food &middot; target: D-glucose `glucose`

> acid then enzyme

**Primary feedstocks** (2)

- amylose repeat unit `starch-unit`
- water `water`

**Intermediates** (2)

- D-glucose `glucose`
- maltose `maltose`

**Products and byproducts** (1)

- D-fructose `fructose`

| # | step | in | out | conditions | class |
|--:|---|---|---|---|---|
| 1 | acid or enzymatic hydrolysis | starch-unit + water | maltose | alpha-amylase, 360 K | `glycoside-hydrolysis` |
| 2 | saccharification | maltose + water | glucose | glucoamylase, 330 K | `glycoside-hydrolysis` |
| 3 | isomerisation to HFCS | glucose | fructose | glucose isomerase, 330 K | `isomerisation` |

<a id="vanillin-eugenol"></a>

### vanillin from eugenol

`vanillin-eugenol` &middot; flavours &middot; target: 4-hydroxy-3-methoxybenzaldehyde `vanillin`

> clove oil isomerisation and oxidation

**Primary feedstocks** (2)

- eugenol `eugenol`
- dioxygen `oxygen`

**Intermediates** (1)

- isoeugenol `isoeugenol`

**Products and byproducts** (2)

- ethanal `acetaldehyde`
- 4-hydroxy-3-methoxybenzaldehyde `vanillin`

**Catalysts** (both sides of one step, net stoichiometry zero)

- sodium hydroxide `sodium-hydroxide`

| # | step | in | out | conditions | class |
|--:|---|---|---|---|---|
| 1 | isomerisation | eugenol + sodium-hydroxide | isoeugenol + sodium-hydroxide | 470 K, KOH | `alkene-isomerisation` |
| 2 | side-chain oxidation | isoeugenol + oxygen | vanillin + acetaldehyde | nitrobenzene or air, alkaline | `oxidative-cleavage` |

<a id="photography-silver"></a>

### silver halide photography

`photography-silver` &middot; imaging &middot; target: silver metal `silver`

> expose, develop, fix

**Primary feedstocks** (4)

- 1,4-dihydroxybenzene `hydroquinone`
- potassium iodide `potassium-iodide`
- silver nitrate `silver-nitrate`
- sodium thiosulfate `sodium-thiosulfate`

**Intermediates** (1)

- silver iodide `silver-iodide`

**Products and byproducts** (7)

- 1,4-benzoquinone `benzoquinone`
- hydrogen iodide `hydrogen-iodide`
- diiodine `iodine`
- potassium nitrate `potassium-nitrate`
- silver metal `silver`
- sodium dithiosulfatoargentate `silver-thiosulfate-complex`
- sodium iodide `sodium-iodide`

| # | step | in | out | conditions | class |
|--:|---|---|---|---|---|
| 1 | emulsion precipitation | silver-nitrate + potassium-iodide | silver-iodide + potassium-nitrate | gelatin emulsion, dark | `precipitation-metathesis` |
| 2 | latent image formation | silver-iodide | silver + iodine | photons, silver speck nucleation | `photoreduction` |
| 3 | development | silver-iodide + hydroquinone | silver + benzoquinone + hydrogen-iodide | alkaline developer, 293 K | `chemical-reduction` |
| 4 | fixing | silver-iodide + sodium-thiosulfate | silver-thiosulfate-complex + sodium-iodide | hypo bath | `complexation-dissolution` |

<a id="strecker-amino-acid"></a>

### Strecker amino acid synthesis

`strecker-amino-acid` &middot; fine-chemicals &middot; target: L-alanine `alanine`

> aldehyde, ammonia, cyanide

**Primary feedstocks** (4)

- ethanal `acetaldehyde`
- ammonia `ammonia`
- hydrogen chloride `hydrogen-chloride`
- hydrogen cyanide `hydrogen-cyanide`

**Intermediates** (3)

- 2-aminopropanenitrile `2-aminopropanenitrile`
- ethanimine `ethanimine`
- water `water`

**Products and byproducts** (2)

- L-alanine `alanine`
- ammonium chloride `ammonium-chloride`

| # | step | in | out | conditions | class |
|--:|---|---|---|---|---|
| 1 | imine formation | acetaldehyde + ammonia | ethanimine + water | aqueous, ambient | `imine-formation` |
| 2 | cyanide addition | ethanimine + hydrogen-cyanide | 2-aminopropanenitrile | ambient | `nucleophilic-addition` |
| 3 | nitrile hydrolysis | 2-aminopropanenitrile + water + hydrogen-chloride | alanine + ammonium-chloride | reflux, dilute acid | `nitrile-hydrolysis` |

<a id="gabriel-synthesis"></a>

### Gabriel primary amine synthesis

`gabriel-synthesis` &middot; fine-chemicals &middot; target: benzylamine `benzylamine`

> phthalimide alkylation and cleavage

**Primary feedstocks** (4)

- benzyl chloride `benzyl-chloride`
- hydrazine `hydrazine`
- phthalimide `phthalimide`
- potassium hydroxide `potassium-hydroxide`

**Intermediates** (2)

- N-benzylphthalimide `n-benzylphthalimide`
- potassium phthalimide `potassium-phthalimide`

**Products and byproducts** (4)

- benzylamine `benzylamine`
- phthalhydrazide `phthalhydrazide`
- potassium chloride `potassium-chloride`
- water `water`

| # | step | in | out | conditions | class |
|--:|---|---|---|---|---|
| 1 | salt formation | phthalimide + potassium-hydroxide | potassium-phthalimide + water | ethanol, reflux | `imide-deprotonation` |
| 2 | alkylation | potassium-phthalimide + benzyl-chloride | n-benzylphthalimide + potassium-chloride | DMF, 370 K | `nucleophilic-substitution` |
| 3 | hydrazinolysis | n-benzylphthalimide + hydrazine | benzylamine + phthalhydrazide | ethanol, reflux | `hydrazinolysis` |

<a id="malonic-ester-synthesis"></a>

### malonic ester synthesis

`malonic-ester-synthesis` &middot; fine-chemicals &middot; target: pentanoic acid `valeric-acid`

> alkylate, hydrolyse, decarboxylate

**Primary feedstocks** (5)

- 1-bromopropane `1-bromopropane`
- diethyl malonate `diethyl-malonate`
- sodium ethoxide `sodium-ethoxide`
- sodium hydroxide `sodium-hydroxide`
- water `water`

**Intermediates** (3)

- diethyl propylmalonate `diethyl-propylmalonate`
- diethyl malonate anion `malonate-anion`
- propylmalonic acid `propylmalonic-acid`

**Products and byproducts** (4)

- bromide ion `bromide-ion`
- carbon dioxide `carbon-dioxide`
- ethanol `ethanol`
- pentanoic acid `valeric-acid`

| # | step | in | out | conditions | class |
|--:|---|---|---|---|---|
| 1 | deprotonation | diethyl-malonate + sodium-ethoxide | malonate-anion + ethanol | ethanol, ambient | `carbanion-generation` |
| 2 | alkylation | malonate-anion + 1-bromopropane | diethyl-propylmalonate + bromide-ion | reflux | `nucleophilic-substitution` |
| 3 | hydrolysis | diethyl-propylmalonate + water + sodium-hydroxide | propylmalonic-acid + ethanol | saponify then acidify | `ester-hydrolysis` |
| 4 | decarboxylation | propylmalonic-acid | valeric-acid + carbon-dioxide | 420 K | `decarboxylation` |

<a id="acetoacetic-ester-synthesis"></a>

### acetoacetic ester synthesis

`acetoacetic-ester-synthesis` &middot; fine-chemicals &middot; target: 2-pentanone `2-pentanone`

> the methyl ketone route

**Primary feedstocks** (4)

- bromoethane `bromoethane`
- ethyl acetoacetate `ethyl-acetoacetate`
- sodium ethoxide `sodium-ethoxide`
- water `water`

**Intermediates** (2)

- ethyl acetoacetate anion `acetoacetate-anion`
- ethyl 2-ethylacetoacetate `ethyl-2-ethylacetoacetate`

**Products and byproducts** (4)

- 2-pentanone `2-pentanone`
- bromide ion `bromide-ion`
- carbon dioxide `carbon-dioxide`
- ethanol `ethanol`

| # | step | in | out | conditions | class |
|--:|---|---|---|---|---|
| 1 | deprotonation | ethyl-acetoacetate + sodium-ethoxide | acetoacetate-anion + ethanol | ethanol | `carbanion-generation` |
| 2 | alkylation | acetoacetate-anion + bromoethane | ethyl-2-ethylacetoacetate + bromide-ion | reflux | `nucleophilic-substitution` |
| 3 | hydrolysis and decarboxylation | ethyl-2-ethylacetoacetate + water | 2-pentanone + carbon-dioxide + ethanol | dilute acid, reflux | `ester-hydrolysis-decarboxylation` |

<a id="aldol-route"></a>

### aldol condensation

`aldol-route` &middot; fine-chemicals &middot; target: 2-butenal `crotonaldehyde`

> the C-C bond that built industry

**Primary feedstocks** (2)

- ethanal `acetaldehyde`
- hydroxide ion `hydroxide`

**Intermediates** (2)

- 3-hydroxybutanal `3-hydroxybutanal`
- acetaldehyde enolate `enolate-acetaldehyde`

**Products and byproducts** (2)

- 2-butenal `crotonaldehyde`
- water `water`

| # | step | in | out | conditions | class |
|--:|---|---|---|---|---|
| 1 | enolate formation | acetaldehyde + hydroxide | enolate-acetaldehyde + water | dilute base, 278 K | `carbanion-generation` |
| 2 | aldol addition | enolate-acetaldehyde + acetaldehyde | 3-hydroxybutanal | cold, dilute | `aldol-addition` |
| 3 | dehydration | 3-hydroxybutanal | crotonaldehyde + water | warming, acid or base | `dehydration` |

<a id="claisen-route"></a>

### Claisen ester condensation

`claisen-route` &middot; fine-chemicals &middot; target: ethyl acetoacetate `ethyl-acetoacetate`

> ester enolate acylation

**Primary feedstocks** (2)

- ethyl acetate `ethyl-acetate`
- sodium ethoxide `sodium-ethoxide`

**Intermediates** (1)

- ethyl acetate enolate `ethyl-acetate-enolate`

**Products and byproducts** (3)

- ethanol `ethanol`
- ethoxide ion `ethoxide-ion`
- ethyl acetoacetate `ethyl-acetoacetate`

| # | step | in | out | conditions | class |
|--:|---|---|---|---|---|
| 1 | ester enolate | ethyl-acetate + sodium-ethoxide | ethyl-acetate-enolate + ethanol | dry ethanol | `carbanion-generation` |
| 2 | acylation | ethyl-acetate-enolate + ethyl-acetate | ethyl-acetoacetate + ethoxide-ion | reflux | `claisen-condensation` |

<a id="friedel-crafts-route"></a>

### Friedel-Crafts alkylation and acylation

`friedel-crafts-route` &middot; aromatics &middot; target: acetophenone `acetophenone`

> aluminium chloride catalysis

**Primary feedstocks** (2)

- acetyl chloride `acetyl-chloride`
- benzene `benzene`

**Intermediates** (1)

- acetylium ion `acylium-acetyl`

**Products and byproducts** (2)

- acetophenone `acetophenone`
- hydrogen chloride `hydrogen-chloride`

**Catalysts** (both sides of one step, net stoichiometry zero)

- aluminium chloride `aluminium-chloride`

| # | step | in | out | conditions | class |
|--:|---|---|---|---|---|
| 1 | acylium generation | acetyl-chloride + aluminium-chloride | acylium-acetyl + aluminium-chloride | DCM, 273 K | `lewis-acid-activation` |
| 2 | aromatic acylation | benzene + acylium-acetyl | acetophenone + hydrogen-chloride | 273 to 298 K | `friedel-crafts-acylation` |

<a id="cannizzaro-route"></a>

### Cannizzaro disproportionation

`cannizzaro-route` &middot; fine-chemicals &middot; target: benzyl alcohol `benzyl-alcohol`

> no alpha hydrogen, so it disproportionates

**Primary feedstocks** (2)

- benzaldehyde `benzaldehyde`
- sodium hydroxide `sodium-hydroxide`

**Intermediates** (0)

- *(none: a single-step route has no intermediate by definition)*

**Products and byproducts** (2)

- benzyl alcohol `benzyl-alcohol`
- sodium benzoate `sodium-benzoate`

| # | step | in | out | conditions | class |
|--:|---|---|---|---|---|
| 1 | disproportionation | benzaldehyde + sodium-hydroxide | benzyl-alcohol + sodium-benzoate | 50% NaOH, 340 K | `cannizzaro-disproportionation` |

<a id="perkin-route"></a>

### Perkin cinnamic acid synthesis

`perkin-route` &middot; flavours &middot; target: trans-cinnamic acid `cinnamic-acid`

> benzaldehyde plus acetic anhydride

**Primary feedstocks** (3)

- acetic anhydride `acetic-anhydride`
- benzaldehyde `benzaldehyde`
- sodium acetate `sodium-acetate`

**Intermediates** (0)

- *(none: a single-step route has no intermediate by definition)*

**Products and byproducts** (2)

- ethanoic acid `acetic-acid`
- trans-cinnamic acid `cinnamic-acid`

| # | step | in | out | conditions | class |
|--:|---|---|---|---|---|
| 1 | condensation | benzaldehyde + acetic-anhydride + sodium-acetate | cinnamic-acid + acetic-acid | 450 K, 8 h | `perkin-condensation` |

<a id="knoevenagel-route"></a>

### Knoevenagel condensation

`knoevenagel-route` &middot; fine-chemicals &middot; target: trans-cinnamic acid `cinnamic-acid`

> active methylene plus aldehyde

**Primary feedstocks** (2)

- benzaldehyde `benzaldehyde`
- propanedioic acid `malonic-acid`

**Intermediates** (0)

- *(none: a single-step route has no intermediate by definition)*

**Products and byproducts** (3)

- carbon dioxide `carbon-dioxide`
- trans-cinnamic acid `cinnamic-acid`
- water `water`

**Catalysts** (both sides of one step, net stoichiometry zero)

- piperidine `piperidine`

| # | step | in | out | conditions | class |
|--:|---|---|---|---|---|
| 1 | condensation | benzaldehyde + malonic-acid + piperidine | cinnamic-acid + carbon-dioxide + water + piperidine | pyridine, reflux | `knoevenagel-doebner-condensation` |

<a id="beckmann-route"></a>

### Beckmann rearrangement

`beckmann-route` &middot; polymers &middot; target: epsilon-caprolactam `caprolactam`

> oxime to amide

**Primary feedstocks** (2)

- cyclohexanone `cyclohexanone`
- hydroxylamine `hydroxylamine`

**Intermediates** (1)

- cyclohexanone oxime `cyclohexanone-oxime`

**Products and byproducts** (2)

- epsilon-caprolactam `caprolactam`
- water `water`

**Catalysts** (both sides of one step, net stoichiometry zero)

- sulfuric acid `sulfuric-acid`

| # | step | in | out | conditions | class |
|--:|---|---|---|---|---|
| 1 | oxime formation | cyclohexanone + hydroxylamine | cyclohexanone-oxime + water | pH 5 | `oxime-formation` |
| 2 | rearrangement | cyclohexanone-oxime + sulfuric-acid | caprolactam + sulfuric-acid | oleum, 400 K | `beckmann-rearrangement` |

<a id="hofmann-route"></a>

### Hofmann rearrangement

`hofmann-route` &middot; fine-chemicals &middot; target: phenylamine `aniline`

> amide to amine, one carbon shorter

**Primary feedstocks** (3)

- benzamide `benzamide`
- sodium hydroxide `sodium-hydroxide`
- sodium hypochlorite `sodium-hypochlorite`

**Intermediates** (3)

- N-bromobenzamide `n-bromobenzamide`
- phenyl isocyanate `phenyl-isocyanate`
- water `water`

**Products and byproducts** (4)

- phenylamine `aniline`
- carbon dioxide `carbon-dioxide`
- sodium bromide `sodium-bromide`
- sodium chloride `sodium-chloride`

| # | step | in | out | conditions | class |
|--:|---|---|---|---|---|
| 1 | N-bromination | benzamide + sodium-hypochlorite + sodium-hydroxide | n-bromobenzamide + water + sodium-chloride | 273 K, aqueous | `n-halogenation` |
| 2 | rearrangement to the isocyanate | n-bromobenzamide + sodium-hydroxide | phenyl-isocyanate + sodium-bromide + water | 340 K | `hofmann-rearrangement` |
| 3 | hydrolysis | phenyl-isocyanate + water | aniline + carbon-dioxide | aqueous | `isocyanate-hydrolysis` |

<a id="curtius-route"></a>

### Curtius rearrangement

`curtius-route` &middot; fine-chemicals &middot; target: phenylamine `aniline`

> acyl azide to isocyanate to amine

**Primary feedstocks** (3)

- benzoyl chloride `benzoyl-chloride`
- hydrazoic acid `hydrazoic-acid`
- water `water`

**Intermediates** (2)

- benzoyl azide `benzoyl-azide`
- phenyl isocyanate `phenyl-isocyanate`

**Products and byproducts** (4)

- phenylamine `aniline`
- carbon dioxide `carbon-dioxide`
- hydrogen chloride `hydrogen-chloride`
- dinitrogen `nitrogen`

| # | step | in | out | conditions | class |
|--:|---|---|---|---|---|
| 1 | acyl azide formation | benzoyl-chloride + hydrazoic-acid | benzoyl-azide + hydrogen-chloride | 273 K | `nucleophilic-acyl-substitution` |
| 2 | thermal rearrangement | benzoyl-azide | phenyl-isocyanate + nitrogen | 350 K, toluene | `curtius-rearrangement` |
| 3 | hydrolysis | phenyl-isocyanate + water | aniline + carbon-dioxide | aqueous | `isocyanate-hydrolysis` |

<a id="sandmeyer-route"></a>

### Sandmeyer reaction

`sandmeyer-route` &middot; aromatics &middot; target: chlorobenzene `chlorobenzene`

> diazonium to aryl halide

**Primary feedstocks** (3)

- phenylamine `aniline`
- hydrogen chloride `hydrogen-chloride`
- sodium nitrite `sodium-nitrite`

**Intermediates** (1)

- benzenediazonium chloride `benzenediazonium-chloride`

**Products and byproducts** (4)

- chlorobenzene `chlorobenzene`
- dinitrogen `nitrogen`
- sodium chloride `sodium-chloride`
- water `water`

**Catalysts** (both sides of one step, net stoichiometry zero)

- copper(I) oxide `copper-i-oxide`

| # | step | in | out | conditions | class |
|--:|---|---|---|---|---|
| 1 | diazotisation | aniline + sodium-nitrite + hydrogen-chloride | benzenediazonium-chloride + water + sodium-chloride | 273-278 K | `diazotisation` |
| 2 | copper-catalysed substitution | benzenediazonium-chloride + copper-i-oxide | chlorobenzene + nitrogen + copper-i-oxide | CuCl, warming | `sandmeyer-substitution` |

<a id="reimer-tiemann"></a>

### Reimer-Tiemann formylation

`reimer-tiemann` &middot; fine-chemicals &middot; target: 2-hydroxybenzaldehyde `salicylaldehyde`

> dichlorocarbene on phenoxide

**Primary feedstocks** (3)

- trichloromethane `chloroform`
- phenoxide ion `phenoxide-ion`
- sodium hydroxide `sodium-hydroxide`

**Intermediates** (2)

- dichlorocarbene `dichlorocarbene`
- water `water`

**Products and byproducts** (3)

- chloride ion `chloride-ion`
- 2-hydroxybenzaldehyde `salicylaldehyde`
- sodium chloride `sodium-chloride`

| # | step | in | out | conditions | class |
|--:|---|---|---|---|---|
| 1 | carbene generation | chloroform + sodium-hydroxide | dichlorocarbene + sodium-chloride + water | aqueous NaOH, 340 K | `alpha-elimination` |
| 2 | formylation | phenoxide-ion + dichlorocarbene + water | salicylaldehyde + chloride-ion | 340 K | `electrophilic-formylation` |

<a id="williamson-ether"></a>

### Williamson ether synthesis

`williamson-ether` &middot; fine-chemicals &middot; target: methoxybenzene `anisole`

> alkoxide plus alkyl halide

**Primary feedstocks** (3)

- iodomethane `iodomethane`
- phenol `phenol`
- sodium hydroxide `sodium-hydroxide`

**Intermediates** (1)

- sodium phenoxide `sodium-phenoxide`

**Products and byproducts** (3)

- methoxybenzene `anisole`
- sodium iodide `sodium-iodide`
- water `water`

| # | step | in | out | conditions | class |
|--:|---|---|---|---|---|
| 1 | alkoxide formation | phenol + sodium-hydroxide | sodium-phenoxide + water | aqueous or alcoholic | `proton-transfer` |
| 2 | alkylation | sodium-phenoxide + iodomethane | anisole + sodium-iodide | acetone, reflux | `williamson-ether-synthesis` |

<a id="fischer-indole"></a>

### Fischer indole synthesis

`fischer-indole` &middot; heterocycles &middot; target: skatole `3-methylindole`

> phenylhydrazine plus ketone

**Primary feedstocks** (2)

- 2-butanone `butanone`
- phenylhydrazine `phenylhydrazine`

**Intermediates** (1)

- butan-2-one phenylhydrazone `butanone-phenylhydrazone`

**Products and byproducts** (3)

- skatole `3-methylindole`
- ammonia `ammonia`
- water `water`

**Catalysts** (both sides of one step, net stoichiometry zero)

- zinc chloride `zinc-chloride`

| # | step | in | out | conditions | class |
|--:|---|---|---|---|---|
| 1 | hydrazone formation | phenylhydrazine + butanone | butanone-phenylhydrazone + water | ethanol, reflux | `hydrazone-formation` |
| 2 | sigmatropic rearrangement and cyclisation | butanone-phenylhydrazone + zinc-chloride | 3-methylindole + ammonia + zinc-chloride | 450 K, ZnCl2 | `fischer-indolisation` |

<a id="skraup-route"></a>

### Skraup quinoline synthesis

`skraup-route` &middot; heterocycles &middot; target: quinoline `quinoline`

> aniline, glycerol and nitrobenzene

**Primary feedstocks** (2)

- 1,2,3-propanetriol `glycerol`
- nitrobenzene `nitrobenzene`

**Intermediates** (1)

- 2-propenal `acrolein`

**Products and byproducts** (2)

- quinoline `quinoline`
- water `water`

**Catalysts** (both sides of one step, net stoichiometry zero)

- phenylamine `aniline`
- sulfuric acid `sulfuric-acid`

| # | step | in | out | conditions | class |
|--:|---|---|---|---|---|
| 1 | glycerol dehydration | glycerol + sulfuric-acid | acrolein + water + sulfuric-acid | 420 K, in situ | `dehydration` |
| 2 | Michael addition and cyclisation | aniline + acrolein + nitrobenzene + sulfuric-acid | quinoline + aniline + water + sulfuric-acid | violent reflux, nitrobenzene oxidant | `skraup-cyclisation` |

<a id="hantzsch-pyridine"></a>

### Hantzsch dihydropyridine synthesis

`hantzsch-pyridine` &middot; heterocycles &middot; target: pyridine `pyridine`

> two beta-ketoesters, an aldehyde and ammonia

**Primary feedstocks** (4)

- ethanal `acetaldehyde`
- ammonia `ammonia`
- ethyl acetoacetate `ethyl-acetoacetate`
- nitric acid `nitric-acid`

**Intermediates** (1)

- diethyl 1,4-dihydro-2,4,6-trimethylpyridine-3,5-dicarboxylate `hantzsch-dihydropyridine`

**Products and byproducts** (2)

- pyridine `pyridine`
- water `water`

| # | step | in | out | conditions | class |
|--:|---|---|---|---|---|
| 1 | four-component condensation | ethyl-acetoacetate + acetaldehyde + ammonia | hantzsch-dihydropyridine + water | ethanol, reflux | `multicomponent-condensation` |
| 2 | oxidation to the pyridine | hantzsch-dihydropyridine + nitric-acid | pyridine + water | oxidation | `oxidative-aromatisation` |

<a id="wohler-urea"></a>

### Wohler urea synthesis

`wohler-urea` &middot; landmark &middot; target: carbamide `urea`

> the synthesis that ended vitalism

**Primary feedstocks** (2)

- ammonium chloride `ammonium-chloride`
- silver nitrate `silver-nitrate`

**Intermediates** (1)

- ammonium cyanate `ammonium-cyanate`

**Products and byproducts** (2)

- silver chloride `silver-chloride`
- carbamide `urea`

| # | step | in | out | conditions | class |
|--:|---|---|---|---|---|
| 1 | double displacement | silver-nitrate + ammonium-chloride | silver-chloride + ammonium-cyanate | aqueous | `precipitation-metathesis` |
| 2 | isomerisation to urea | ammonium-cyanate | urea | evaporation to dryness, 370 K | `isomerisation` |

<a id="kolbe-electrolysis"></a>

### Kolbe electrolysis

`kolbe-electrolysis` &middot; landmark &middot; target: ethane `ethane`

> carboxylate to dimer

**Primary feedstocks** (2)

- sodium acetate `sodium-acetate`
- water `water`

**Intermediates** (0)

- *(none: a single-step route has no intermediate by definition)*

**Products and byproducts** (4)

- carbon dioxide `carbon-dioxide`
- ethane `ethane`
- hydrogen `hydrogen`
- sodium hydroxide `sodium-hydroxide`

| # | step | in | out | conditions | class |
|--:|---|---|---|---|---|
| 1 | anodic decarboxylation | sodium-acetate + water | ethane + carbon-dioxide + sodium-hydroxide + hydrogen | platinum anode, concentrated | `electro-organic-coupling` |

<a id="haloform-iodoform"></a>

### iodoform test

`haloform-iodoform` &middot; analysis &middot; target: triiodomethane `iodoform`

> methyl ketone plus hypohalite

**Primary feedstocks** (3)

- propanone `acetone`
- diiodine `iodine`
- sodium hydroxide `sodium-hydroxide`

**Intermediates** (1)

- 1,1,1-triiodoacetone `triiodoacetone`

**Products and byproducts** (4)

- triiodomethane `iodoform`
- sodium acetate `sodium-acetate`
- sodium iodide `sodium-iodide`
- water `water`

| # | step | in | out | conditions | class |
|--:|---|---|---|---|---|
| 1 | trihalogenation | acetone + iodine + sodium-hydroxide | triiodoacetone + sodium-iodide + water | aqueous, ambient | `alpha-halogenation` |
| 2 | cleavage | triiodoacetone + sodium-hydroxide | iodoform + sodium-acetate | aqueous | `haloform-cleavage` |

<a id="fehling-test"></a>

### Fehling reducing sugar test

`fehling-test` &middot; analysis &middot; target: copper(I) oxide `copper-i-oxide`

> the brick-red precipitate

**Primary feedstocks** (3)

- copper(II) ion `copper-ii-ion`
- D-glucose `glucose`
- sodium hydroxide `sodium-hydroxide`

**Intermediates** (0)

- *(none: a single-step route has no intermediate by definition)*

**Products and byproducts** (3)

- copper(I) oxide `copper-i-oxide`
- D-gluconic acid `gluconic-acid`
- water `water`

| # | step | in | out | conditions | class |
|--:|---|---|---|---|---|
| 1 | reduction of copper(II) | glucose + copper-ii-ion + sodium-hydroxide | gluconic-acid + copper-i-oxide + water | boiling, tartrate complexed | `metal-ion-aldehyde-oxidation` |

<a id="tollens-test"></a>

### Tollens silver mirror

`tollens-test` &middot; analysis &middot; target: silver metal `silver`

> aldehyde reduces the diamminesilver ion

**Primary feedstocks** (3)

- benzaldehyde `benzaldehyde`
- hydroxide ion `hydroxide`
- silver ion `silver-ion`

**Intermediates** (0)

- *(none: a single-step route has no intermediate by definition)*

**Products and byproducts** (3)

- silver metal `silver`
- sodium benzoate `sodium-benzoate`
- water `water`

**Catalysts** (both sides of one step, net stoichiometry zero)

- ammonia `ammonia`

| # | step | in | out | conditions | class |
|--:|---|---|---|---|---|
| 1 | silver mirror | benzaldehyde + silver-ion + ammonia + hydroxide | sodium-benzoate + silver + water + ammonia | warm, ammoniacal silver nitrate | `metal-ion-aldehyde-oxidation` |

<a id="marsh-test"></a>

### Marsh arsenic test

`marsh-test` &middot; analysis &middot; target: arsine `arsine`

> the forensic classic

**Primary feedstocks** (2)

- sulfuric acid `sulfuric-acid`
- zinc metal `zinc`

**Intermediates** (2)

- arsenic `arsenic`
- arsine `arsine`

**Products and byproducts** (2)

- hydrogen `hydrogen`
- zinc sulfate `zinc-sulfate`

| # | step | in | out | conditions | class |
|--:|---|---|---|---|---|
| 1 | arsine generation | arsenic + zinc + sulfuric-acid | arsine + zinc-sulfate + hydrogen | nascent hydrogen | `dissolving-metal-reduction` |
| 2 | thermal decomposition to the mirror | arsine | arsenic + hydrogen | heated tube | `hydride-thermal-deposition` |

<a id="kjeldahl"></a>

### Kjeldahl nitrogen determination

`kjeldahl` &middot; analysis &middot; target: ammonium sulfate `ammonium-sulfate`

> digest, distil, titrate

**Primary feedstocks** (5)

- boric acid `boric-acid`
- glycine `glycine`
- potassium sulfate `potassium-sulfate`
- sodium hydroxide `sodium-hydroxide`
- sulfuric acid `sulfuric-acid`

**Intermediates** (2)

- ammonia `ammonia`
- ammonium sulfate `ammonium-sulfate`

**Products and byproducts** (5)

- ammonium borate `ammonium-borate`
- carbon dioxide `carbon-dioxide`
- sodium sulfate `sodium-sulfate`
- sulfur dioxide `sulfur-dioxide`
- water `water`

| # | step | in | out | conditions | class |
|--:|---|---|---|---|---|
| 1 | digestion | glycine + sulfuric-acid + potassium-sulfate | ammonium-sulfate + carbon-dioxide + sulfur-dioxide + water | 640 K, copper catalyst | `oxidative-digestion` |
| 2 | distillation | ammonium-sulfate + sodium-hydroxide | ammonia + sodium-sulfate + water | steam distillation | `proton-transfer` |
| 3 | titration | ammonia + boric-acid | ammonium-borate | back-titrated with standard acid | `proton-transfer` |

## 1900s

<a id="claus-process"></a>

### Claus sulfur recovery

`claus-process` &middot; heavy-inorganic &middot; target: sulfur (S8 crown) `sulfur-s8`

> H2S to elemental sulfur

**Primary feedstocks** (2)

- hydrogen sulfide `hydrogen-sulfide`
- dioxygen `oxygen`

**Intermediates** (1)

- sulfur dioxide `sulfur-dioxide`

**Products and byproducts** (2)

- sulfur (S8 crown) `sulfur-s8`
- water `water`

| # | step | in | out | conditions | class |
|--:|---|---|---|---|---|
| 1 | partial combustion of H2S | hydrogen-sulfide + oxygen | sulfur-dioxide + water | thermal stage | `combustion` |
| 2 | Claus reaction | hydrogen-sulfide + sulfur-dioxide | sulfur-s8 + water | catalytic stage, alumina | `comproportionation` |

<a id="haber-bosch"></a>

### Haber-Bosch ammonia

`haber-bosch` &middot; heavy-inorganic &middot; target: ammonia `ammonia`

> the nitrogen fixation that fed the century

**Primary feedstocks** (2)

- hydrogen `hydrogen`
- dinitrogen `nitrogen`

**Intermediates** (0)

- *(none: a single-step route has no intermediate by definition)*

**Products and byproducts** (1)

- ammonia `ammonia`

**Catalysts** (both sides of one step, net stoichiometry zero)

- iron metal `iron`

| # | step | in | out | conditions | class |
|--:|---|---|---|---|---|
| 1 | ammonia synthesis | nitrogen + hydrogen + iron | ammonia + iron | 700 K, 200 bar, promoted iron | `catalytic-gas-synthesis` |

<a id="ostwald-process"></a>

### Ostwald nitric acid

`ostwald-process` &middot; heavy-inorganic &middot; target: nitric acid `nitric-acid`

> ammonia to NO to NO2 to HNO3

**Primary feedstocks** (2)

- ammonia `ammonia`
- dioxygen `oxygen`

**Intermediates** (3)

- nitric oxide `nitric-oxide`
- nitrogen dioxide `nitrogen-dioxide`
- water `water`

**Products and byproducts** (1)

- nitric acid `nitric-acid`

**Catalysts** (both sides of one step, net stoichiometry zero)

- platinum metal `platinum`

| # | step | in | out | conditions | class |
|--:|---|---|---|---|---|
| 1 | ammonia oxidation | ammonia + oxygen + platinum | nitric-oxide + water + platinum | 1150 K, Pt-Rh gauze | `catalytic-gas-oxidation` |
| 2 | NO oxidation | nitric-oxide + oxygen | nitrogen-dioxide | cooling train | `gas-phase-oxidation` |
| 3 | absorption | nitrogen-dioxide + water | nitric-acid + nitric-oxide | absorption tower | `disproportionation-hydrolysis` |

<a id="birkeland-eyde"></a>

### Birkeland-Eyde arc process

`birkeland-eyde` &middot; heavy-inorganic &middot; target: nitric acid `nitric-acid`

> superseded by Haber plus Ostwald

**Primary feedstocks** (3)

- dinitrogen `nitrogen`
- dioxygen `oxygen`
- water `water`

**Intermediates** (2)

- nitric oxide `nitric-oxide`
- nitrogen dioxide `nitrogen-dioxide`

**Products and byproducts** (1)

- nitric acid `nitric-acid`

| # | step | in | out | conditions | class |
|--:|---|---|---|---|---|
| 1 | arc nitrogen fixation | nitrogen + oxygen | nitric-oxide | electric arc, 3000 K | `thermal-fixation` |
| 2 | NO oxidation | nitric-oxide + oxygen | nitrogen-dioxide | cooling | `gas-phase-oxidation` |
| 3 | absorption | nitrogen-dioxide + water | nitric-acid + nitric-oxide | tower | `disproportionation-hydrolysis` |

<a id="frank-caro"></a>

### Frank-Caro cyanamide process

`frank-caro` &middot; heavy-inorganic &middot; target: calcium cyanamide `calcium-cyanamide`

> nitrogen fixation via carbide

**Primary feedstocks** (3)

- calcium oxide `calcium-oxide`
- dinitrogen `nitrogen`
- water `water`

**Intermediates** (3)

- calcium carbide `calcium-carbide`
- calcium cyanamide `calcium-cyanamide`
- graphite `carbon-graphite`

**Products and byproducts** (3)

- ammonia `ammonia`
- calcium carbonate `calcium-carbonate`
- carbon monoxide `carbon-monoxide`

| # | step | in | out | conditions | class |
|--:|---|---|---|---|---|
| 1 | carbide formation | calcium-oxide + carbon-graphite | calcium-carbide + carbon-monoxide | electric furnace, 2300 K | `carbothermic-reduction` |
| 2 | nitrogen fixation | calcium-carbide + nitrogen | calcium-cyanamide + carbon-graphite | 1300 K | `gas-solid-fixation` |
| 3 | hydrolysis to ammonia | calcium-cyanamide + water | ammonia + calcium-carbonate | steam | `hydrolysis` |

<a id="andrussow"></a>

### Andrussow HCN process

`andrussow` &middot; heavy-inorganic &middot; target: hydrogen cyanide `hydrogen-cyanide`

> methane, ammonia and air over platinum

**Primary feedstocks** (3)

- ammonia `ammonia`
- methane `methane`
- dioxygen `oxygen`

**Intermediates** (0)

- *(none: a single-step route has no intermediate by definition)*

**Products and byproducts** (2)

- hydrogen cyanide `hydrogen-cyanide`
- water `water`

**Catalysts** (both sides of one step, net stoichiometry zero)

- platinum metal `platinum`

| # | step | in | out | conditions | class |
|--:|---|---|---|---|---|
| 1 | ammoxidation of methane | methane + ammonia + oxygen + platinum | hydrogen-cyanide + water + platinum | 1400 K, Pt gauze | `ammoxidation` |

<a id="hypochlorite-bleach"></a>

### sodium hypochlorite bleach

`hypochlorite-bleach` &middot; heavy-inorganic &middot; target: sodium hypochlorite `sodium-hypochlorite`

> chlorine into caustic

**Primary feedstocks** (2)

- dichlorine `chlorine`
- sodium hydroxide `sodium-hydroxide`

**Intermediates** (0)

- *(none: a single-step route has no intermediate by definition)*

**Products and byproducts** (3)

- sodium chloride `sodium-chloride`
- sodium hypochlorite `sodium-hypochlorite`
- water `water`

| # | step | in | out | conditions | class |
|--:|---|---|---|---|---|
| 1 | chlorine into caustic | chlorine + sodium-hydroxide | sodium-hypochlorite + sodium-chloride + water | cold, dilute | `disproportionation` |

<a id="phosphoric-wet"></a>

### wet-process phosphoric acid

`phosphoric-wet` &middot; heavy-inorganic &middot; target: phosphoric acid `phosphoric-acid`

> phosphate rock plus sulfuric acid; gypsum byproduct

**Primary feedstocks** (3)

- tricalcium phosphate `calcium-phosphate`
- sulfuric acid `sulfuric-acid`
- water `water`

**Intermediates** (0)

- *(none: a single-step route has no intermediate by definition)*

**Products and byproducts** (2)

- gypsum `gypsum`
- phosphoric acid `phosphoric-acid`

| # | step | in | out | conditions | class |
|--:|---|---|---|---|---|
| 1 | rock digestion | calcium-phosphate + sulfuric-acid + water | phosphoric-acid + gypsum | 350 K | `acid-displacement-precipitating` |

<a id="downs-cell"></a>

### Downs cell sodium

`downs-cell` &middot; metallurgy &middot; target: sodium metal `sodium`

> molten NaCl electrolysis

**Primary feedstocks** (1)

- sodium chloride `sodium-chloride`

**Intermediates** (0)

- *(none: a single-step route has no intermediate by definition)*

**Products and byproducts** (2)

- dichlorine `chlorine`
- sodium metal `sodium`

| # | step | in | out | conditions | class |
|--:|---|---|---|---|---|
| 1 | molten salt electrolysis | sodium-chloride | sodium + chlorine | 900 K melt, CaCl2 flux | `electrolysis` |

<a id="tnt-route"></a>

### TNT manufacture

`tnt-route` &middot; energetics &middot; target: 2,4,6-trinitrotoluene `tnt`

> three-stage nitration of toluene

**Primary feedstocks** (3)

- disulfuric acid (oleum) `disulfuric-acid`
- nitric acid `nitric-acid`
- toluene `toluene`

**Intermediates** (2)

- 2,4-dinitrotoluene `2,4-dinitrotoluene`
- 2-nitrotoluene `2-nitrotoluene`

**Products and byproducts** (2)

- 2,4,6-trinitrotoluene `tnt`
- water `water`

**Catalysts** (both sides of one step, net stoichiometry zero)

- sulfuric acid `sulfuric-acid`

| # | step | in | out | conditions | class |
|--:|---|---|---|---|---|
| 1 | mononitration | toluene + nitric-acid + sulfuric-acid | 2-nitrotoluene + water + sulfuric-acid | 300 K | `electrophilic-aromatic-nitration` |
| 2 | dinitration | 2-nitrotoluene + nitric-acid + sulfuric-acid | 2,4-dinitrotoluene + water + sulfuric-acid | 340 K | `electrophilic-aromatic-nitration` |
| 3 | trinitration | 2,4-dinitrotoluene + nitric-acid + disulfuric-acid | tnt + water + sulfuric-acid | 390 K, oleum | `electrophilic-aromatic-nitration` |

<a id="rdx-route"></a>

### RDX from hexamine

`rdx-route` &middot; energetics &middot; target: cyclotrimethylenetrinitramine `rdx`

> nitrolysis of hexamine

**Primary feedstocks** (2)

- ammonia `ammonia`
- nitric acid `nitric-acid`

**Intermediates** (2)

- methanal `formaldehyde`
- hexamine `hexamethylenetetramine`

**Products and byproducts** (2)

- cyclotrimethylenetrinitramine `rdx`
- water `water`

| # | step | in | out | conditions | class |
|--:|---|---|---|---|---|
| 1 | hexamine formation | formaldehyde + ammonia | hexamethylenetetramine + water | aqueous, ambient | `condensation` |
| 2 | nitrolysis | hexamethylenetetramine + nitric-acid | rdx + formaldehyde + water | 290 K, 99% HNO3 | `nitrolysis` |

<a id="petn-route"></a>

### PETN from pentaerythritol

`petn-route` &middot; energetics &middot; target: pentaerythritol tetranitrate `petn`

> nitration of the tetraol

**Primary feedstocks** (4)

- ethanal `acetaldehyde`
- calcium hydroxide `calcium-hydroxide`
- methanal `formaldehyde`
- nitric acid `nitric-acid`

**Intermediates** (1)

- pentaerythritol `pentaerythritol`

**Products and byproducts** (3)

- calcium formate `calcium-formate`
- pentaerythritol tetranitrate `petn`
- water `water`

| # | step | in | out | conditions | class |
|--:|---|---|---|---|---|
| 1 | pentaerythritol from aldol | acetaldehyde + formaldehyde + calcium-hydroxide | pentaerythritol + calcium-formate | aldol then crossed Cannizzaro | `aldol-cannizzaro` |
| 2 | nitration | pentaerythritol + nitric-acid | petn + water | 295 K, conc HNO3 | `esterification-nitration` |

<a id="phenol-cumene"></a>

### cumene (Hock) process

`phenol-cumene` &middot; petrochemical &middot; target: phenol `phenol`

> phenol and acetone from one radical chain

**Primary feedstocks** (3)

- benzene `benzene`
- dioxygen `oxygen`
- propene `propylene`

**Intermediates** (2)

- isopropylbenzene `cumene`
- cumene hydroperoxide `cumene-hydroperoxide`

**Products and byproducts** (2)

- propanone `acetone`
- phenol `phenol`

**Catalysts** (both sides of one step, net stoichiometry zero)

- phosphoric acid `phosphoric-acid`
- sulfuric acid `sulfuric-acid`

| # | step | in | out | conditions | class |
|--:|---|---|---|---|---|
| 1 | Friedel-Crafts alkylation | benzene + propylene + phosphoric-acid | cumene + phosphoric-acid | 520 K, solid phosphoric acid | `friedel-crafts-alkylation` |
| 2 | autoxidation | cumene + oxygen | cumene-hydroperoxide | 380 K, air, radical chain | `autoxidation` |
| 3 | Hock rearrangement | cumene-hydroperoxide + sulfuric-acid | phenol + acetone + sulfuric-acid | 340 K, dilute acid | `hock-rearrangement` |

<a id="phenol-dow"></a>

### Dow chlorobenzene hydrolysis

`phenol-dow` &middot; petrochemical &middot; target: phenol `phenol`

> high-pressure caustic

**Primary feedstocks** (3)

- benzene `benzene`
- dichlorine `chlorine`
- sodium hydroxide `sodium-hydroxide`

**Intermediates** (3)

- chlorobenzene `chlorobenzene`
- hydrogen chloride `hydrogen-chloride`
- sodium phenoxide `sodium-phenoxide`

**Products and byproducts** (2)

- phenol `phenol`
- sodium chloride `sodium-chloride`

**Catalysts** (both sides of one step, net stoichiometry zero)

- iron(III) chloride `iron-iii-chloride`

| # | step | in | out | conditions | class |
|--:|---|---|---|---|---|
| 1 | benzene chlorination | benzene + chlorine + iron-iii-chloride | chlorobenzene + hydrogen-chloride + iron-iii-chloride | 320 K, Lewis acid | `electrophilic-aromatic-halogenation` |
| 2 | caustic hydrolysis | chlorobenzene + sodium-hydroxide | sodium-phenoxide + sodium-chloride | 620 K, 300 bar | `nucleophilic-aromatic-substitution` |
| 3 | acidification | sodium-phenoxide + hydrogen-chloride | phenol + sodium-chloride | ambient | `proton-transfer` |

<a id="bakelite-route"></a>

### Bakelite phenolic resin

`bakelite-route` &middot; polymers &middot; target: phenol-formaldehyde resin unit `bakelite-unit`

> the first fully synthetic plastic

**Primary feedstocks** (2)

- methanal `formaldehyde`
- phenol `phenol`

**Intermediates** (1)

- resole repeat unit `resole-unit`

**Products and byproducts** (2)

- phenol-formaldehyde resin unit `bakelite-unit`
- water `water`

**Catalysts** (both sides of one step, net stoichiometry zero)

- sodium hydroxide `sodium-hydroxide`

| # | step | in | out | conditions | class |
|--:|---|---|---|---|---|
| 1 | methylolation | phenol + formaldehyde + sodium-hydroxide | resole-unit + sodium-hydroxide | base, 340 K | `electrophilic-hydroxymethylation` |
| 2 | condensation and cure | resole-unit + phenol | bakelite-unit + water | 420 K, pressure | `polycondensation` |

<a id="paracetamol-route"></a>

### paracetamol

`paracetamol-route` &middot; pharma &middot; target: acetaminophen `paracetamol`

> nitrobenzene to 4-aminophenol to the amide

**Primary feedstocks** (3)

- acetic anhydride `acetic-anhydride`
- hydrogen `hydrogen`
- nitrobenzene `nitrobenzene`

**Intermediates** (2)

- 4-aminophenol `4-aminophenol`
- N-phenylhydroxylamine `phenylhydroxylamine`

**Products and byproducts** (3)

- ethanoic acid `acetic-acid`
- acetaminophen `paracetamol`
- water `water`

**Catalysts** (both sides of one step, net stoichiometry zero)

- platinum metal `platinum`
- sulfuric acid `sulfuric-acid`

| # | step | in | out | conditions | class |
|--:|---|---|---|---|---|
| 1 | nitrobenzene reduction to the hydroxylamine | nitrobenzene + hydrogen + platinum | phenylhydroxylamine + water + platinum | controlled hydrogenation | `nitro-partial-hydrogenation` |
| 2 | Bamberger rearrangement | phenylhydroxylamine + sulfuric-acid | 4-aminophenol + sulfuric-acid | dilute acid, 340 K | `bamberger-rearrangement` |
| 3 | acetylation | 4-aminophenol + acetic-anhydride | paracetamol + acetic-acid | aqueous, 360 K | `n-acylation` |

<a id="sulfa-drug-route"></a>

### sulfanilamide

`sulfa-drug-route` &middot; pharma &middot; target: sulfanilamide `sulfanilamide`

> acetanilide, chlorosulfonation, ammonolysis

**Primary feedstocks** (4)

- acetic anhydride `acetic-anhydride`
- ammonia `ammonia`
- phenylamine `aniline`
- chlorosulfonic acid `chlorosulfonic-acid`

**Intermediates** (5)

- 4-acetamidobenzenesulfonamide `4-acetamidobenzenesulfonamide`
- 4-acetamidobenzenesulfonyl chloride `4-acetamidobenzenesulfonyl-chloride`
- N-phenylacetamide `acetanilide`
- hydrogen chloride `hydrogen-chloride`
- water `water`

**Products and byproducts** (3)

- ethanoic acid `acetic-acid`
- ammonium chloride `ammonium-chloride`
- sulfanilamide `sulfanilamide`

| # | step | in | out | conditions | class |
|--:|---|---|---|---|---|
| 1 | aniline protection | aniline + acetic-anhydride | acetanilide + acetic-acid | 370 K | `n-acylation` |
| 2 | chlorosulfonation | acetanilide + chlorosulfonic-acid | 4-acetamidobenzenesulfonyl-chloride + hydrogen-chloride + water | 340 K, excess ClSO3H | `electrophilic-aromatic-sulfonation` |
| 3 | ammonolysis | 4-acetamidobenzenesulfonyl-chloride + ammonia | 4-acetamidobenzenesulfonamide + ammonium-chloride | aqueous ammonia | `sulfonamide-formation` |
| 4 | deprotection | 4-acetamidobenzenesulfonamide + water + hydrogen-chloride | sulfanilamide + acetic-acid | dilute HCl, reflux | `amide-hydrolysis` |

<a id="prontosil-route"></a>

### prontosil

`prontosil-route` &middot; pharma &middot; target: prontosil `prontosil`

> the azo prodrug

**Primary feedstocks** (3)

- 1,3-diaminobenzene `m-phenylenediamine`
- sodium nitrite `sodium-nitrite`
- sulfanilamide `sulfanilamide`

**Intermediates** (2)

- hydrogen chloride `hydrogen-chloride`
- sulfanilamide diazonium chloride `sulfanilamide-diazonium`

**Products and byproducts** (3)

- prontosil `prontosil`
- sodium chloride `sodium-chloride`
- water `water`

| # | step | in | out | conditions | class |
|--:|---|---|---|---|---|
| 1 | diazotisation | sulfanilamide + sodium-nitrite + hydrogen-chloride | sulfanilamide-diazonium + water + sodium-chloride | 278 K | `diazotisation` |
| 2 | azo coupling | sulfanilamide-diazonium + m-phenylenediamine | prontosil + hydrogen-chloride | cold, buffered | `azo-coupling` |

<a id="penicillin-route"></a>

### penicillin fermentation and semisynthesis

`penicillin-route` &middot; pharma &middot; target: amoxicillin `amoxicillin`

> 6-APA as the branch point

**Primary feedstocks** (3)

- D-4-hydroxyphenylglycine `4-hydroxyphenylglycine`
- ammonium sulfate `ammonium-sulfate`
- D-glucose `glucose`

**Intermediates** (4)

- 6-aminopenicillanic acid `6-apa`
- benzylpenicillin `penicillin-g`
- phenylacetic acid `phenylacetic-acid`
- water `water`

**Products and byproducts** (2)

- amoxicillin `amoxicillin`
- carbon dioxide `carbon-dioxide`

| # | step | in | out | conditions | class |
|--:|---|---|---|---|---|
| 1 | fermentation | glucose + ammonium-sulfate + phenylacetic-acid | penicillin-g + carbon-dioxide + water | Penicillium, deep tank, 300 K | `fermentation` |
| 2 | enzymatic deacylation | penicillin-g + water | 6-apa + phenylacetic-acid | penicillin acylase, pH 8 | `amide-hydrolysis` |
| 3 | reacylation | 6-apa + 4-hydroxyphenylglycine | amoxicillin + water | enzymatic or chemical coupling | `amide-coupling` |

<a id="aspirin-impurity"></a>

### aspirin hydrolysis and impurities

`aspirin-impurity` &middot; pharma &middot; target: 2-hydroxybenzoic acid `salicylic-acid`

> why old aspirin smells of vinegar

**Primary feedstocks** (2)

- acetylsalicylic acid `aspirin`
- water `water`

**Intermediates** (0)

- *(none: a single-step route has no intermediate by definition)*

**Products and byproducts** (2)

- ethanoic acid `acetic-acid`
- 2-hydroxybenzoic acid `salicylic-acid`

| # | step | in | out | conditions | class |
|--:|---|---|---|---|---|
| 1 | ester hydrolysis | aspirin + water | salicylic-acid + acetic-acid | humidity, months | `ester-hydrolysis` |

<a id="ddt-route"></a>

### DDT

`ddt-route` &middot; agrochemical &middot; target: dichlorodiphenyltrichloroethane `ddt`

> chloral plus chlorobenzene

**Primary feedstocks** (2)

- chloral `chloral`
- chlorobenzene `chlorobenzene`

**Intermediates** (0)

- *(none: a single-step route has no intermediate by definition)*

**Products and byproducts** (2)

- dichlorodiphenyltrichloroethane `ddt`
- water `water`

**Catalysts** (both sides of one step, net stoichiometry zero)

- sulfuric acid `sulfuric-acid`

| # | step | in | out | conditions | class |
|--:|---|---|---|---|---|
| 1 | condensation | chloral + chlorobenzene + sulfuric-acid | ddt + water + sulfuric-acid | conc H2SO4, 290 K | `friedel-crafts-hydroxyalkylation` |

<a id="freon-route"></a>

### Freon-12 from carbon tetrachloride

`freon-route` &middot; refrigerants &middot; target: dichlorodifluoromethane `dichlorodifluoromethane`

> Swarts halogen exchange

**Primary feedstocks** (2)

- tetrachloromethane `carbon-tetrachloride`
- hydrogen fluoride `hydrogen-fluoride`

**Intermediates** (0)

- *(none: a single-step route has no intermediate by definition)*

**Products and byproducts** (2)

- dichlorodifluoromethane `dichlorodifluoromethane`
- hydrogen chloride `hydrogen-chloride`

**Catalysts** (both sides of one step, net stoichiometry zero)

- antimony pentachloride `antimony-pentachloride`

| # | step | in | out | conditions | class |
|--:|---|---|---|---|---|
| 1 | halogen exchange | carbon-tetrachloride + hydrogen-fluoride + antimony-pentachloride | dichlorodifluoromethane + hydrogen-chloride + antimony-pentachloride | 340 K, SbF3/SbCl5 | `swarts-halogen-exchange` |

<a id="ptfe-route"></a>

### PTFE from chlorodifluoromethane

`ptfe-route` &middot; polymers &middot; target: polytetrafluoroethylene repeat unit `ptfe-unit`

> pyrolysis to TFE then polymerisation

**Primary feedstocks** (3)

- trichloromethane `chloroform`
- hydrogen fluoride `hydrogen-fluoride`
- potassium persulfate `potassium-persulfate`

**Intermediates** (2)

- chlorodifluoromethane `chlorodifluoromethane`
- tetrafluoroethene `tetrafluoroethylene`

**Products and byproducts** (2)

- hydrogen chloride `hydrogen-chloride`
- polytetrafluoroethylene repeat unit `ptfe-unit`

**Catalysts** (both sides of one step, net stoichiometry zero)

- antimony pentachloride `antimony-pentachloride`

| # | step | in | out | conditions | class |
|--:|---|---|---|---|---|
| 1 | HCFC-22 synthesis | chloroform + hydrogen-fluoride + antimony-pentachloride | chlorodifluoromethane + hydrogen-chloride + antimony-pentachloride | 340 K | `swarts-halogen-exchange` |
| 2 | pyrolysis to TFE | chlorodifluoromethane | tetrafluoroethylene + hydrogen-chloride | 970 K, short contact | `pyrolysis` |
| 3 | emulsion polymerisation | tetrafluoroethylene + potassium-persulfate | ptfe-unit | 350 K, 20 bar, water | `radical-polymerisation` |

<a id="steam-reforming"></a>

### steam methane reforming

`steam-reforming` &middot; syngas &middot; target: hydrogen `hydrogen`

> the hydrogen and syngas backbone

**Primary feedstocks** (2)

- methane `methane`
- water `water`

**Intermediates** (0)

- *(none: a single-step route has no intermediate by definition)*

**Products and byproducts** (2)

- carbon monoxide `carbon-monoxide`
- hydrogen `hydrogen`

**Catalysts** (both sides of one step, net stoichiometry zero)

- nickel metal `nickel`

| # | step | in | out | conditions | class |
|--:|---|---|---|---|---|
| 1 | methane reforming | methane + water + nickel | carbon-monoxide + hydrogen + nickel | 1100 K, 25 bar, Ni | `steam-reforming` |

<a id="methanol-synthesis"></a>

### methanol from syngas

`methanol-synthesis` &middot; syngas &middot; target: methanol `methanol`

> copper-zinc catalyst

**Primary feedstocks** (3)

- carbon dioxide `carbon-dioxide`
- carbon monoxide `carbon-monoxide`
- hydrogen `hydrogen`

**Intermediates** (0)

- *(none: a single-step route has no intermediate by definition)*

**Products and byproducts** (2)

- methanol `methanol`
- water `water`

**Catalysts** (both sides of one step, net stoichiometry zero)

- copper metal `copper`

| # | step | in | out | conditions | class |
|--:|---|---|---|---|---|
| 1 | CO hydrogenation | carbon-monoxide + hydrogen + copper | methanol + copper | 520 K, 80 bar, Cu/ZnO | `catalytic-gas-synthesis` |
| 2 | CO2 hydrogenation | carbon-dioxide + hydrogen + copper | methanol + water + copper | same reactor | `catalytic-gas-synthesis` |

<a id="fischer-tropsch"></a>

### Fischer-Tropsch synthesis

`fischer-tropsch` &middot; syngas &middot; target: n-octane `octane`

> syngas to liquid hydrocarbons

**Primary feedstocks** (2)

- carbon monoxide `carbon-monoxide`
- hydrogen `hydrogen`

**Intermediates** (0)

- *(none: a single-step route has no intermediate by definition)*

**Products and byproducts** (2)

- n-octane `octane`
- water `water`

**Catalysts** (both sides of one step, net stoichiometry zero)

- iron metal `iron`

| # | step | in | out | conditions | class |
|--:|---|---|---|---|---|
| 1 | chain growth | carbon-monoxide + hydrogen + iron | octane + water + iron | 500 K, 25 bar, Fe or Co | `fischer-tropsch` |

<a id="monsanto-acetic"></a>

### Monsanto / Cativa acetic acid

`monsanto-acetic` &middot; petrochemical &middot; target: ethanoic acid `acetic-acid`

> methanol carbonylation

**Primary feedstocks** (2)

- carbon monoxide `carbon-monoxide`
- methanol `methanol`

**Intermediates** (3)

- hydrogen iodide `hydrogen-iodide`
- iodomethane `iodomethane`
- water `water`

**Products and byproducts** (1)

- ethanoic acid `acetic-acid`

| # | step | in | out | conditions | class |
|--:|---|---|---|---|---|
| 1 | methanol to methyl iodide | methanol + hydrogen-iodide | iodomethane + water | in situ | `nucleophilic-substitution` |
| 2 | carbonylation | iodomethane + carbon-monoxide + water | acetic-acid + hydrogen-iodide | 460 K, 35 bar, Rh or Ir | `carbonylation` |

<a id="acetic-anhydride-ketene"></a>

### acetic anhydride via ketene

`acetic-anhydride-ketene` &middot; petrochemical &middot; target: acetic anhydride `acetic-anhydride`

> acetic acid pyrolysis

**Primary feedstocks** (1)

- ethanoic acid `acetic-acid`

**Intermediates** (1)

- ethenone `ketene`

**Products and byproducts** (2)

- acetic anhydride `acetic-anhydride`
- water `water`

| # | step | in | out | conditions | class |
|--:|---|---|---|---|---|
| 1 | acetic acid pyrolysis | acetic-acid | ketene + water | 1000 K, triethyl-phosphate catalyst | `pyrolysis-dehydration` |
| 2 | ketene absorption | ketene + acetic-acid | acetic-anhydride | 320 K | `nucleophilic-addition` |

<a id="wacker-process"></a>

### Wacker oxidation

`wacker-process` &middot; petrochemical &middot; target: ethanal `acetaldehyde`

> palladium-copper, ethylene to acetaldehyde

**Primary feedstocks** (2)

- ethene `ethylene`
- dioxygen `oxygen`

**Intermediates** (0)

- *(none: a single-step route has no intermediate by definition)*

**Products and byproducts** (1)

- ethanal `acetaldehyde`

**Catalysts** (both sides of one step, net stoichiometry zero)

- copper(II) ion `copper-ii-ion`

| # | step | in | out | conditions | class |
|--:|---|---|---|---|---|
| 1 | ethylene oxidation | ethylene + oxygen + copper-ii-ion | acetaldehyde + copper-ii-ion | PdCl2/CuCl2, 400 K | `wacker-oxidation` |

<a id="steam-cracking"></a>

### steam cracking of naphtha

`steam-cracking` &middot; petrochemical &middot; target: ethene `ethylene`

> the modern olefin source

**Primary feedstocks** (2)

- n-octane `octane`
- water `water`

**Intermediates** (0)

- *(none: a single-step route has no intermediate by definition)*

**Products and byproducts** (5)

- 1,3-butadiene `1,3-butadiene`
- ethene `ethylene`
- hydrogen `hydrogen`
- methane `methane`
- propene `propylene`

| # | step | in | out | conditions | class |
|--:|---|---|---|---|---|
| 1 | thermal cracking | octane + water | ethylene + propylene + 1,3-butadiene + methane + hydrogen | 1100 K, steam diluted, 0.5 s | `thermal-cracking` |

<a id="ethylene-oxide-route"></a>

### ethylene oxide by direct oxidation

`ethylene-oxide-route` &middot; petrochemical &middot; target: oxirane `ethylene-oxide`

> silver catalyst

**Primary feedstocks** (2)

- ethene `ethylene`
- dioxygen `oxygen`

**Intermediates** (0)

- *(none: a single-step route has no intermediate by definition)*

**Products and byproducts** (3)

- carbon dioxide `carbon-dioxide`
- oxirane `ethylene-oxide`
- water `water`

**Catalysts** (both sides of one step, net stoichiometry zero)

- silver metal `silver`

| # | step | in | out | conditions | class |
|--:|---|---|---|---|---|
| 1 | silver-catalysed epoxidation | ethylene + oxygen + silver | ethylene-oxide + silver | 520 K, 20 bar, Ag on alumina | `catalytic-epoxidation` |
| 2 | combustion side reaction | ethylene + oxygen | carbon-dioxide + water | same reactor, selectivity loss | `combustion` |

<a id="chlorohydrin-route"></a>

### chlorohydrin route to ethylene oxide

`chlorohydrin-route` &middot; petrochemical &middot; target: oxirane `ethylene-oxide`

> the route silver replaced

**Primary feedstocks** (3)

- calcium hydroxide `calcium-hydroxide`
- dichlorine `chlorine`
- ethene `ethylene`

**Intermediates** (2)

- 2-chloroethanol `2-chloroethanol`
- water `water`

**Products and byproducts** (3)

- calcium chloride `calcium-chloride`
- oxirane `ethylene-oxide`
- hydrogen chloride `hydrogen-chloride`

| # | step | in | out | conditions | class |
|--:|---|---|---|---|---|
| 1 | chlorohydrination | ethylene + chlorine + water | 2-chloroethanol + hydrogen-chloride | 310 K, aqueous | `halohydrin-formation` |
| 2 | ring closure | 2-chloroethanol + calcium-hydroxide | ethylene-oxide + calcium-chloride + water | lime slurry, 370 K | `intramolecular-williamson` |

<a id="ethylene-glycol-route"></a>

### ethylene glycol by EO hydration

`ethylene-glycol-route` &middot; petrochemical &middot; target: 1,2-ethanediol `ethylene-glycol`

> di- and tri-glycol as byproducts

**Primary feedstocks** (2)

- oxirane `ethylene-oxide`
- water `water`

**Intermediates** (2)

- diethylene glycol `diethylene-glycol`
- 1,2-ethanediol `ethylene-glycol`

**Products and byproducts** (1)

- triethylene glycol `triethylene-glycol`

| # | step | in | out | conditions | class |
|--:|---|---|---|---|---|
| 1 | hydration | ethylene-oxide + water | ethylene-glycol | 470 K, 20 bar, excess water | `epoxide-hydrolysis` |
| 2 | oligomer byproducts | ethylene-oxide + ethylene-glycol | diethylene-glycol | same reactor | `epoxide-alkoxylation` |
| 3 | further oligomerisation | ethylene-oxide + diethylene-glycol | triethylene-glycol | same reactor | `epoxide-alkoxylation` |

<a id="pet-route"></a>

### PET polyester

`pet-route` &middot; polymers &middot; target: poly(ethylene terephthalate) repeat unit `pet-unit`

> terephthalic acid or DMT plus glycol

**Primary feedstocks** (2)

- dimethyl terephthalate `dimethyl-terephthalate`
- 1,4-benzenedicarboxylic acid `terephthalic-acid`

**Intermediates** (2)

- bis(2-hydroxyethyl) terephthalate `bis-hydroxyethyl-terephthalate`
- 1,2-ethanediol `ethylene-glycol`

**Products and byproducts** (3)

- methanol `methanol`
- poly(ethylene terephthalate) repeat unit `pet-unit`
- water `water`

| # | step | in | out | conditions | class |
|--:|---|---|---|---|---|
| 1 | esterification | terephthalic-acid + ethylene-glycol | bis-hydroxyethyl-terephthalate + water | 530 K | `esterification` |
| 2 | polycondensation | bis-hydroxyethyl-terephthalate | pet-unit + ethylene-glycol | 560 K, vacuum, antimony catalyst | `polycondensation` |
| 3 | DMT alternative | dimethyl-terephthalate + ethylene-glycol | bis-hydroxyethyl-terephthalate + methanol | 470 K, transesterification | `transesterification` |

<a id="p-xylene-oxidation"></a>

### Amoco terephthalic acid

`p-xylene-oxidation` &middot; polymers &middot; target: 1,4-benzenedicarboxylic acid `terephthalic-acid`

> cobalt-manganese-bromide air oxidation

**Primary feedstocks** (2)

- dioxygen `oxygen`
- para-xylene `p-xylene`

**Intermediates** (0)

- *(none: a single-step route has no intermediate by definition)*

**Products and byproducts** (2)

- 1,4-benzenedicarboxylic acid `terephthalic-acid`
- water `water`

**Catalysts** (both sides of one step, net stoichiometry zero)

- ethanoic acid `acetic-acid`
- cobalt metal `cobalt`

| # | step | in | out | conditions | class |
|--:|---|---|---|---|---|
| 1 | Amoco air oxidation | p-xylene + oxygen + acetic-acid + cobalt | terephthalic-acid + water + acetic-acid + cobalt | 470 K, 20 bar, Co/Mn/Br | `catalytic-air-oxidation` |

<a id="nylon66-route"></a>

### nylon 66

`nylon66-route` &middot; polymers &middot; target: nylon 66 repeat unit `nylon-66-unit`

> Carothers; adipic acid plus HMDA

**Primary feedstocks** (3)

- hexanedioic acid `adipic-acid`
- hexanedinitrile `adiponitrile`
- hydrogen `hydrogen`

**Intermediates** (2)

- 1,6-diaminohexane `hexamethylenediamine`
- nylon 66 salt `nylon-66-salt`

**Products and byproducts** (2)

- nylon 66 repeat unit `nylon-66-unit`
- water `water`

**Catalysts** (both sides of one step, net stoichiometry zero)

- nickel metal `nickel`

| # | step | in | out | conditions | class |
|--:|---|---|---|---|---|
| 1 | adiponitrile hydrogenation | adiponitrile + hydrogen + nickel | hexamethylenediamine + nickel | 400 K, 300 bar, Raney Ni | `nitrile-hydrogenation` |
| 2 | nylon salt formation | adipic-acid + hexamethylenediamine | nylon-66-salt | methanol, ambient, stoichiometry control | `proton-transfer` |
| 3 | melt polycondensation | nylon-66-salt | nylon-66-unit + water | 550 K, autoclave then vacuum | `polycondensation` |

<a id="nylon6-route"></a>

### nylon 6 from caprolactam

`nylon6-route` &middot; polymers &middot; target: nylon 6 repeat unit `nylon-6-unit`

> cyclohexanone oxime and the Beckmann rearrangement

**Primary feedstocks** (4)

- ammonia `ammonia`
- cyclohexanone `cyclohexanone`
- disulfuric acid (oleum) `disulfuric-acid`
- hydroxylamine `hydroxylamine`

**Intermediates** (4)

- epsilon-caprolactam `caprolactam`
- cyclohexanone oxime `cyclohexanone-oxime`
- sulfuric acid `sulfuric-acid`
- water `water`

**Products and byproducts** (2)

- ammonium sulfate `ammonium-sulfate`
- nylon 6 repeat unit `nylon-6-unit`

| # | step | in | out | conditions | class |
|--:|---|---|---|---|---|
| 1 | oxime formation | cyclohexanone + hydroxylamine | cyclohexanone-oxime + water | pH 5, 340 K | `oxime-formation` |
| 2 | Beckmann rearrangement | cyclohexanone-oxime + disulfuric-acid | caprolactam + sulfuric-acid | oleum, 400 K | `beckmann-rearrangement` |
| 3 | neutralisation | sulfuric-acid + ammonia | ammonium-sulfate | the fertiliser co-product | `proton-transfer` |
| 4 | ring-opening polymerisation | caprolactam + water | nylon-6-unit | 530 K, hydrolytic ROP | `ring-opening-polymerisation` |

<a id="adipic-acid-route"></a>

### adipic acid from cyclohexane

`adipic-acid-route` &middot; polymers &middot; target: hexanedioic acid `adipic-acid`

> KA oil then nitric acid oxidation

**Primary feedstocks** (3)

- cyclohexane `cyclohexane`
- nitric acid `nitric-acid`
- dioxygen `oxygen`

**Intermediates** (2)

- cyclohexanol `cyclohexanol`
- cyclohexanone `cyclohexanone`

**Products and byproducts** (3)

- hexanedioic acid `adipic-acid`
- nitrous oxide `nitrous-oxide`
- water `water`

**Catalysts** (both sides of one step, net stoichiometry zero)

- cobalt metal `cobalt`

| # | step | in | out | conditions | class |
|--:|---|---|---|---|---|
| 1 | cyclohexane autoxidation | cyclohexane + oxygen + cobalt | cyclohexanol + cyclohexanone + water + cobalt | 430 K, air, low conversion | `autoxidation` |
| 2 | nitric acid oxidation | cyclohexanol + nitric-acid | adipic-acid + nitrous-oxide + water | 350 K, Cu/V catalyst | `nitric-acid-oxidation` |
| 3 | ketone oxidation | cyclohexanone + nitric-acid | adipic-acid + nitrous-oxide + water | same reactor | `nitric-acid-oxidation` |

<a id="acrylonitrile-sohio"></a>

### SOHIO ammoxidation

`acrylonitrile-sohio` &middot; polymers &middot; target: 2-propenenitrile `acrylonitrile`

> propylene, ammonia and air

**Primary feedstocks** (3)

- ammonia `ammonia`
- dioxygen `oxygen`
- propene `propylene`

**Intermediates** (0)

- *(none: a single-step route has no intermediate by definition)*

**Products and byproducts** (5)

- ethanenitrile `acetonitrile`
- 2-propenenitrile `acrylonitrile`
- carbon dioxide `carbon-dioxide`
- hydrogen cyanide `hydrogen-cyanide`
- water `water`

| # | step | in | out | conditions | class |
|--:|---|---|---|---|---|
| 1 | propylene ammoxidation | propylene + ammonia + oxygen | acrylonitrile + water | 720 K, Bi-Mo oxide, fluid bed | `ammoxidation` |
| 2 | acetonitrile byproduct | propylene + ammonia + oxygen | acetonitrile + carbon-dioxide + water | same reactor | `ammoxidation` |
| 3 | HCN byproduct | propylene + ammonia + oxygen | hydrogen-cyanide + water | same reactor | `ammoxidation` |

<a id="adiponitrile-route"></a>

### adiponitrile by electrohydrodimerisation

`adiponitrile-route` &middot; polymers &middot; target: hexanedinitrile `adiponitrile`

> Monsanto electro-organic process

**Primary feedstocks** (2)

- 2-propenenitrile `acrylonitrile`
- water `water`

**Intermediates** (0)

- *(none: a single-step route has no intermediate by definition)*

**Products and byproducts** (2)

- hexanedinitrile `adiponitrile`
- dioxygen `oxygen`

| # | step | in | out | conditions | class |
|--:|---|---|---|---|---|
| 1 | electrohydrodimerisation | acrylonitrile + water | adiponitrile + oxygen | cathode, aqueous emulsion | `electro-organic-coupling` |

<a id="vinyl-chloride-route"></a>

### vinyl chloride and PVC

`vinyl-chloride-route` &middot; polymers &middot; target: poly(vinyl chloride) repeat unit `pvc-unit`

> EDC cracking

**Primary feedstocks** (4)

- dibenzoyl peroxide `benzoyl-peroxide`
- dichlorine `chlorine`
- ethene `ethylene`
- dioxygen `oxygen`

**Intermediates** (3)

- 1,2-dichloroethane `1,2-dichloroethane`
- hydrogen chloride `hydrogen-chloride`
- chloroethene `vinyl-chloride`

**Products and byproducts** (2)

- poly(vinyl chloride) repeat unit `pvc-unit`
- water `water`

**Catalysts** (both sides of one step, net stoichiometry zero)

- copper(II) ion `copper-ii-ion`
- iron(III) chloride `iron-iii-chloride`

| # | step | in | out | conditions | class |
|--:|---|---|---|---|---|
| 1 | direct chlorination | ethylene + chlorine + iron-iii-chloride | 1,2-dichloroethane + iron-iii-chloride | 340 K, liquid phase | `halogen-addition` |
| 2 | oxychlorination | ethylene + hydrogen-chloride + oxygen + copper-ii-ion | 1,2-dichloroethane + water + copper-ii-ion | 520 K, CuCl2 on alumina | `oxychlorination` |
| 3 | EDC cracking | 1,2-dichloroethane | vinyl-chloride + hydrogen-chloride | 770 K, tube furnace | `dehydrohalogenation` |
| 4 | suspension polymerisation | vinyl-chloride + benzoyl-peroxide | pvc-unit | 330 K, 10 bar, water suspension | `radical-polymerisation` |

<a id="styrene-route"></a>

### styrene from ethylbenzene

`styrene-route` &middot; polymers &middot; target: styrene `styrene`

> alkylation then dehydrogenation

**Primary feedstocks** (3)

- benzene `benzene`
- dibenzoyl peroxide `benzoyl-peroxide`
- ethene `ethylene`

**Intermediates** (2)

- ethylbenzene `ethylbenzene`
- styrene `styrene`

**Products and byproducts** (2)

- hydrogen `hydrogen`
- polystyrene repeat unit `polystyrene-unit`

**Catalysts** (both sides of one step, net stoichiometry zero)

- aluminium chloride `aluminium-chloride`
- iron(III) oxide `iron-iii-oxide`

| # | step | in | out | conditions | class |
|--:|---|---|---|---|---|
| 1 | benzene alkylation | benzene + ethylene + aluminium-chloride | ethylbenzene + aluminium-chloride | 400 K, Lewis acid or zeolite | `friedel-crafts-alkylation` |
| 2 | dehydrogenation | ethylbenzene + iron-iii-oxide | styrene + hydrogen + iron-iii-oxide | 900 K, steam diluted, Fe2O3-K | `catalytic-dehydrogenation` |
| 3 | bulk polymerisation | styrene + benzoyl-peroxide | polystyrene-unit | 400 K, thermal or radical | `radical-polymerisation` |

<a id="polyethylene-route"></a>

### polyethylene

`polyethylene-route` &middot; polymers &middot; target: polyethylene repeat unit `polyethylene-unit`

> radical high pressure and Ziegler-Natta

**Primary feedstocks** (2)

- ethene `ethylene`
- dioxygen `oxygen`

**Intermediates** (0)

- *(none: a single-step route has no intermediate by definition)*

**Products and byproducts** (1)

- polyethylene repeat unit `polyethylene-unit`

**Catalysts** (both sides of one step, net stoichiometry zero)

- titanium tetrachloride `titanium-tetrachloride`
- triethylaluminium `triethylaluminium`

| # | step | in | out | conditions | class |
|--:|---|---|---|---|---|
| 1 | high-pressure radical route | ethylene + oxygen | polyethylene-unit | 570 K, 2000 bar, LDPE | `radical-polymerisation` |
| 2 | Ziegler-Natta route | ethylene + titanium-tetrachloride + triethylaluminium | polyethylene-unit + titanium-tetrachloride + triethylaluminium | 350 K, 10 bar, HDPE | `coordination-polymerisation` |

<a id="mma-ach"></a>

### MMA by the acetone cyanohydrin route

`mma-ach` &middot; polymers &middot; target: methyl methacrylate `methyl-methacrylate`

> ammonium bisulfate byproduct

**Primary feedstocks** (5)

- propanone `acetone`
- dibenzoyl peroxide `benzoyl-peroxide`
- hydrogen cyanide `hydrogen-cyanide`
- methanol `methanol`
- sulfuric acid `sulfuric-acid`

**Intermediates** (3)

- acetone cyanohydrin `acetone-cyanohydrin`
- methacrylamide sulfate `methacrylamide-sulfate`
- methyl methacrylate `methyl-methacrylate`

**Products and byproducts** (2)

- ammonium bisulfate `ammonium-bisulfate`
- poly(methyl methacrylate) repeat unit `pmma-unit`

| # | step | in | out | conditions | class |
|--:|---|---|---|---|---|
| 1 | cyanohydrin formation | acetone + hydrogen-cyanide | acetone-cyanohydrin | base catalysed, 290 K | `cyanohydrin-formation` |
| 2 | amide and dehydration | acetone-cyanohydrin + sulfuric-acid | methacrylamide-sulfate | 410 K, conc H2SO4 | `ritter-type-hydration` |
| 3 | esterification | methacrylamide-sulfate + methanol | methyl-methacrylate + ammonium-bisulfate | 400 K | `esterification` |
| 4 | polymerisation | methyl-methacrylate + benzoyl-peroxide | pmma-unit | 340 K, cast sheet | `radical-polymerisation` |

<a id="bisphenol-a-route"></a>

### bisphenol A and polycarbonate

`bisphenol-a-route` &middot; polymers &middot; target: bisphenol A polycarbonate repeat unit `polycarbonate-unit`

> acetone plus phenol, then phosgene

**Primary feedstocks** (4)

- propanone `acetone`
- phenol `phenol`
- phosgene `phosgene`
- sodium hydroxide `sodium-hydroxide`

**Intermediates** (1)

- bisphenol A `bisphenol-a`

**Products and byproducts** (3)

- bisphenol A polycarbonate repeat unit `polycarbonate-unit`
- sodium chloride `sodium-chloride`
- water `water`

**Catalysts** (both sides of one step, net stoichiometry zero)

- hydrogen chloride `hydrogen-chloride`

| # | step | in | out | conditions | class |
|--:|---|---|---|---|---|
| 1 | condensation | phenol + acetone + hydrogen-chloride | bisphenol-a + water + hydrogen-chloride | 340 K, HCl or ion-exchange resin | `friedel-crafts-hydroxyalkylation` |
| 2 | interfacial phosgenation | bisphenol-a + phosgene + sodium-hydroxide | polycarbonate-unit + sodium-chloride + water | DCM/water interface, 300 K | `interfacial-polycondensation` |

<a id="epoxy-route"></a>

### epoxy resin from epichlorohydrin

`epoxy-route` &middot; polymers &middot; target: bisphenol A diglycidyl ether `diglycidyl-ether-bpa`

> glycerol or propylene route to ECH

**Primary feedstocks** (5)

- bisphenol A `bisphenol-a`
- calcium hydroxide `calcium-hydroxide`
- dichlorine `chlorine`
- propene `propylene`
- sodium hydroxide `sodium-hydroxide`

**Intermediates** (4)

- 1,3-dichloro-2-propanol `1,3-dichloro-2-propanol`
- 3-chloropropene `allyl-chloride`
- epichlorohydrin `epichlorohydrin`
- water `water`

**Products and byproducts** (4)

- calcium chloride `calcium-chloride`
- bisphenol A diglycidyl ether `diglycidyl-ether-bpa`
- hydrogen chloride `hydrogen-chloride`
- sodium chloride `sodium-chloride`

| # | step | in | out | conditions | class |
|--:|---|---|---|---|---|
| 1 | allyl chloride from propylene | propylene + chlorine | allyl-chloride + hydrogen-chloride | 770 K, high temperature | `allylic-chlorination` |
| 2 | chlorohydrination | allyl-chloride + chlorine + water | 1,3-dichloro-2-propanol + hydrogen-chloride | aqueous, 310 K | `halohydrin-formation` |
| 3 | ring closure | 1,3-dichloro-2-propanol + calcium-hydroxide | epichlorohydrin + calcium-chloride + water | lime, 370 K | `intramolecular-williamson` |
| 4 | resin formation | bisphenol-a + epichlorohydrin + sodium-hydroxide | diglycidyl-ether-bpa + sodium-chloride + water | 350 K | `williamson-ether-synthesis` |

<a id="polyurethane-route"></a>

### polyurethane from TDI

`polyurethane-route` &middot; polymers &middot; target: polyurethane repeat unit (TDI/diol) `polyurethane-unit`

> dinitrotoluene to diamine to diisocyanate

**Primary feedstocks** (5)

- hydrogen `hydrogen`
- nitric acid `nitric-acid`
- phosgene `phosgene`
- poly(propylene glycol) repeat unit `polypropylene-glycol-unit`
- toluene `toluene`

**Intermediates** (4)

- 2,4-dinitrotoluene `2,4-dinitrotoluene`
- 2,4-toluene diisocyanate `toluene-diisocyanate`
- 2,4-toluenediamine `toluenediamine`
- water `water`

**Products and byproducts** (3)

- carbon dioxide `carbon-dioxide`
- hydrogen chloride `hydrogen-chloride`
- polyurethane repeat unit (TDI/diol) `polyurethane-unit`

**Catalysts** (both sides of one step, net stoichiometry zero)

- nickel metal `nickel`
- sulfuric acid `sulfuric-acid`

| # | step | in | out | conditions | class |
|--:|---|---|---|---|---|
| 1 | toluene dinitration | toluene + nitric-acid + sulfuric-acid | 2,4-dinitrotoluene + water + sulfuric-acid | mixed acid, two stages | `electrophilic-aromatic-nitration` |
| 2 | hydrogenation to the diamine | 2,4-dinitrotoluene + hydrogen + nickel | toluenediamine + water + nickel | 370 K, 30 bar | `nitro-hydrogenation` |
| 3 | phosgenation | toluenediamine + phosgene | toluene-diisocyanate + hydrogen-chloride | 370 K, chlorobenzene solvent | `phosgenation` |
| 4 | foam formation | toluene-diisocyanate + polypropylene-glycol-unit + water | polyurethane-unit + carbon-dioxide | ambient, amine and tin catalysts | `polyaddition` |

<a id="mdi-route"></a>

### MDI from aniline and formaldehyde

`mdi-route` &middot; polymers &middot; target: 4,4-methylenediphenyl diisocyanate `mdi`

> condensation then phosgenation

**Primary feedstocks** (3)

- phenylamine `aniline`
- methanal `formaldehyde`
- phosgene `phosgene`

**Intermediates** (1)

- 4,4-methylenedianiline `methylenedianiline`

**Products and byproducts** (2)

- 4,4-methylenediphenyl diisocyanate `mdi`
- water `water`

**Catalysts** (both sides of one step, net stoichiometry zero)

- hydrogen chloride `hydrogen-chloride`

| # | step | in | out | conditions | class |
|--:|---|---|---|---|---|
| 1 | aniline-formaldehyde condensation | aniline + formaldehyde + hydrogen-chloride | methylenedianiline + water + hydrogen-chloride | 370 K, HCl | `condensation` |
| 2 | phosgenation | methylenedianiline + phosgene | mdi + hydrogen-chloride | 370 K, chlorobenzene | `phosgenation` |

<a id="urea-formaldehyde-route"></a>

### urea-formaldehyde resin

`urea-formaldehyde-route` &middot; polymers &middot; target: urea-formaldehyde resin unit `urea-formaldehyde-unit`

> particleboard adhesive

**Primary feedstocks** (2)

- methanal `formaldehyde`
- carbamide `urea`

**Intermediates** (1)

- monomethylolurea `monomethylolurea`

**Products and byproducts** (2)

- urea-formaldehyde resin unit `urea-formaldehyde-unit`
- water `water`

| # | step | in | out | conditions | class |
|--:|---|---|---|---|---|
| 1 | methylolation | urea + formaldehyde | monomethylolurea | pH 8, 330 K | `nucleophilic-addition` |
| 2 | acid cure | monomethylolurea | urea-formaldehyde-unit + water | pH 4, 380 K, press | `polycondensation` |

<a id="melamine-route"></a>

### melamine from urea

`melamine-route` &middot; polymers &middot; target: 1,3,5-triazine-2,4,6-triamine `melamine`

> urea pyrolysis via cyanic acid

**Primary feedstocks** (1)

- carbamide `urea`

**Intermediates** (1)

- cyanic acid `cyanic-acid`

**Products and byproducts** (3)

- ammonia `ammonia`
- carbon dioxide `carbon-dioxide`
- 1,3,5-triazine-2,4,6-triamine `melamine`

| # | step | in | out | conditions | class |
|--:|---|---|---|---|---|
| 1 | urea pyrolysis | urea | cyanic-acid + ammonia | 620 K | `urea-deammoniation` |
| 2 | trimerisation | cyanic-acid | melamine + carbon-dioxide | 670 K, 80 bar | `trimerisation` |

<a id="silicone-route"></a>

### silicones by the direct process

`silicone-route` &middot; polymers &middot; target: PDMS repeat unit `polydimethylsiloxane-unit`

> Rochow-Muller

**Primary feedstocks** (3)

- chloromethane `chloromethane`
- silicon `silicon`
- water `water`

**Intermediates** (2)

- dichlorodimethylsilane `dichlorodimethylsilane`
- PDMS repeat unit `polydimethylsiloxane-unit`

**Products and byproducts** (2)

- hydrogen chloride `hydrogen-chloride`
- octamethylcyclotetrasiloxane `octamethylcyclotetrasiloxane`

**Catalysts** (both sides of one step, net stoichiometry zero)

- copper metal `copper`

| # | step | in | out | conditions | class |
|--:|---|---|---|---|---|
| 1 | direct process | chloromethane + silicon + copper | dichlorodimethylsilane + copper | 570 K, Cu catalyst, fluid bed | `direct-process` |
| 2 | hydrolysis | dichlorodimethylsilane + water | polydimethylsiloxane-unit + hydrogen-chloride | aqueous, ambient | `hydrolysis-condensation` |
| 3 | cyclic equilibration | polydimethylsiloxane-unit | octamethylcyclotetrasiloxane | 420 K, KOH, vacuum strip | `equilibration` |

<a id="neoprene-route"></a>

### neoprene from acetylene

`neoprene-route` &middot; polymers &middot; target: polychloroprene repeat unit `polychloroprene-unit`

> vinylacetylene then HCl

**Primary feedstocks** (3)

- ethyne `acetylene`
- hydrogen chloride `hydrogen-chloride`
- potassium persulfate `potassium-persulfate`

**Intermediates** (2)

- 2-chloro-1,3-butadiene `chloroprene`
- but-1-en-3-yne `vinylacetylene`

**Products and byproducts** (1)

- polychloroprene repeat unit `polychloroprene-unit`

**Catalysts** (both sides of one step, net stoichiometry zero)

- copper(I) oxide `copper-i-oxide`

| # | step | in | out | conditions | class |
|--:|---|---|---|---|---|
| 1 | acetylene dimerisation | acetylene + copper-i-oxide | vinylacetylene + copper-i-oxide | 350 K, Nieuwland catalyst | `alkyne-dimerisation` |
| 2 | HCl addition | vinylacetylene + hydrogen-chloride + copper-i-oxide | chloroprene + copper-i-oxide | 320 K | `hydrohalogenation` |
| 3 | emulsion polymerisation | chloroprene + potassium-persulfate | polychloroprene-unit | 310 K, aqueous emulsion | `radical-polymerisation` |

<a id="buna-rubber"></a>

### Buna synthetic rubber from butadiene

`buna-rubber` &middot; polymers &middot; target: styrene-butadiene rubber marker `sbr-marker`

> butadiene from ethanol or from cracking

**Primary feedstocks** (3)

- ethanol `ethanol`
- potassium persulfate `potassium-persulfate`
- styrene `styrene`

**Intermediates** (1)

- 1,3-butadiene `1,3-butadiene`

**Products and byproducts** (3)

- hydrogen `hydrogen`
- styrene-butadiene rubber marker `sbr-marker`
- water `water`

**Catalysts** (both sides of one step, net stoichiometry zero)

- magnesium oxide `magnesium-oxide`

| # | step | in | out | conditions | class |
|--:|---|---|---|---|---|
| 1 | Lebedev butadiene from ethanol | ethanol + magnesium-oxide | 1,3-butadiene + hydrogen + water + magnesium-oxide | 700 K, MgO-SiO2 | `dehydration-dehydrogenation` |
| 2 | copolymerisation | 1,3-butadiene + styrene + potassium-persulfate | sbr-marker | 280 K, cold emulsion | `radical-copolymerisation` |

<a id="oxo-process"></a>

### hydroformylation (oxo process)

`oxo-process` &middot; petrochemical &middot; target: butanal `butyraldehyde`

> Roelen; alkene plus syngas

**Primary feedstocks** (3)

- carbon monoxide `carbon-monoxide`
- hydrogen `hydrogen`
- propene `propylene`

**Intermediates** (0)

- *(none: a single-step route has no intermediate by definition)*

**Products and byproducts** (2)

- butanal `butyraldehyde`
- 2-methylpropanal `isobutyraldehyde`

**Catalysts** (both sides of one step, net stoichiometry zero)

- cobalt metal `cobalt`

| # | step | in | out | conditions | class |
|--:|---|---|---|---|---|
| 1 | hydroformylation | propylene + carbon-monoxide + hydrogen + cobalt | butyraldehyde + cobalt | 420 K, 200 bar, HCo(CO)4 | `hydroformylation` |
| 2 | branched isomer | propylene + carbon-monoxide + hydrogen + cobalt | isobutyraldehyde + cobalt | same reactor, n:iso selectivity | `hydroformylation` |

<a id="2-ethylhexanol-route"></a>

### 2-ethylhexanol by aldol-oxo

`2-ethylhexanol-route` &middot; petrochemical &middot; target: 2-ethyl-1-hexanol `2-ethylhexanol`

> the plasticiser alcohol

**Primary feedstocks** (2)

- butanal `butyraldehyde`
- hydrogen `hydrogen`

**Intermediates** (1)

- 2-ethyl-2-hexenal `2-ethylhexenal`

**Products and byproducts** (2)

- 2-ethyl-1-hexanol `2-ethylhexanol`
- water `water`

**Catalysts** (both sides of one step, net stoichiometry zero)

- nickel metal `nickel`
- sodium hydroxide `sodium-hydroxide`

| # | step | in | out | conditions | class |
|--:|---|---|---|---|---|
| 1 | aldol condensation | butyraldehyde + sodium-hydroxide | 2-ethylhexenal + water + sodium-hydroxide | 400 K, dilute caustic | `aldol-condensation` |
| 2 | hydrogenation | 2-ethylhexenal + hydrogen + nickel | 2-ethylhexanol + nickel | 420 K, 50 bar | `enal-hydrogenation` |

<a id="dop-route"></a>

### DOP plasticiser

`dop-route` &middot; petrochemical &middot; target: bis(2-ethylhexyl) phthalate `dioctyl-phthalate`

> phthalic anhydride plus 2-ethylhexanol

**Primary feedstocks** (2)

- 2-ethyl-1-hexanol `2-ethylhexanol`
- phthalic anhydride `phthalic-anhydride`

**Intermediates** (0)

- *(none: a single-step route has no intermediate by definition)*

**Products and byproducts** (2)

- bis(2-ethylhexyl) phthalate `dioctyl-phthalate`
- water `water`

**Catalysts** (both sides of one step, net stoichiometry zero)

- para-toluenesulfonic acid `p-toluenesulfonic-acid`

| # | step | in | out | conditions | class |
|--:|---|---|---|---|---|
| 1 | double esterification | phthalic-anhydride + 2-ethylhexanol + p-toluenesulfonic-acid | dioctyl-phthalate + water + p-toluenesulfonic-acid | 480 K, azeotropic water removal | `esterification` |

<a id="phthalic-anhydride-route"></a>

### phthalic anhydride from o-xylene

`phthalic-anhydride-route` &middot; petrochemical &middot; target: phthalic anhydride `phthalic-anhydride`

> vanadium catalysed air oxidation

**Primary feedstocks** (3)

- naphthalene `naphthalene`
- ortho-xylene `o-xylene`
- dioxygen `oxygen`

**Intermediates** (0)

- *(none: a single-step route has no intermediate by definition)*

**Products and byproducts** (3)

- carbon dioxide `carbon-dioxide`
- phthalic anhydride `phthalic-anhydride`
- water `water`

**Catalysts** (both sides of one step, net stoichiometry zero)

- vanadium(V) oxide `vanadium-pentoxide`

| # | step | in | out | conditions | class |
|--:|---|---|---|---|---|
| 1 | o-xylene air oxidation | o-xylene + oxygen + vanadium-pentoxide | phthalic-anhydride + water + vanadium-pentoxide | 650 K, V2O5, fluid bed | `catalytic-air-oxidation` |
| 2 | naphthalene route | naphthalene + oxygen + vanadium-pentoxide | phthalic-anhydride + carbon-dioxide + water + vanadium-pentoxide | 650 K, the older feed | `catalytic-air-oxidation` |

<a id="maleic-anhydride-route"></a>

### maleic anhydride from n-butane

`maleic-anhydride-route` &middot; petrochemical &middot; target: maleic anhydride `maleic-anhydride`

> VPO catalyst

**Primary feedstocks** (2)

- n-butane `butane`
- dioxygen `oxygen`

**Intermediates** (0)

- *(none: a single-step route has no intermediate by definition)*

**Products and byproducts** (2)

- maleic anhydride `maleic-anhydride`
- water `water`

**Catalysts** (both sides of one step, net stoichiometry zero)

- vanadium(V) oxide `vanadium-pentoxide`

| # | step | in | out | conditions | class |
|--:|---|---|---|---|---|
| 1 | butane oxidation | butane + oxygen + vanadium-pentoxide | maleic-anhydride + water + vanadium-pentoxide | 700 K, VPO catalyst | `catalytic-air-oxidation` |

<a id="hydrogenation-margarine"></a>

### fat hardening

`hydrogenation-margarine` &middot; food &middot; target: glyceryl tristearate `tristearin`

> Normann; trans byproducts

**Primary feedstocks** (3)

- hydrogen `hydrogen`
- cis-9-octadecenoic acid `oleic-acid`
- glyceryl trioleate `triolein`

**Intermediates** (0)

- *(none: a single-step route has no intermediate by definition)*

**Products and byproducts** (2)

- trans-9-octadecenoic acid `elaidic-acid`
- glyceryl tristearate `tristearin`

**Catalysts** (both sides of one step, net stoichiometry zero)

- nickel metal `nickel`

| # | step | in | out | conditions | class |
|--:|---|---|---|---|---|
| 1 | fat hardening | triolein + hydrogen + nickel | tristearin + nickel | 450 K, 3 bar, Ni | `alkene-hydrogenation` |
| 2 | trans isomer byproduct | oleic-acid + hydrogen + nickel | elaidic-acid + nickel | partial hydrogenation isomerises | `isomerisation` |

<a id="ethanol-hydration"></a>

### ethanol by ethylene hydration

`ethanol-hydration` &middot; petrochemical &middot; target: ethanol `ethanol`

> phosphoric acid on silica

**Primary feedstocks** (1)

- ethene `ethylene`

**Intermediates** (2)

- ethanol `ethanol`
- water `water`

**Products and byproducts** (1)

- diethyl ether `diethyl-ether`

**Catalysts** (both sides of one step, net stoichiometry zero)

- phosphoric acid `phosphoric-acid`

| # | step | in | out | conditions | class |
|--:|---|---|---|---|---|
| 1 | acid-catalysed hydration | ethylene + water + phosphoric-acid | ethanol + phosphoric-acid | 570 K, 70 bar, H3PO4 on silica | `alkene-hydration` |
| 2 | ether byproduct | ethanol + ethanol + phosphoric-acid | diethyl-ether + water + phosphoric-acid | same reactor, 410 K | `ether-condensation` |

<a id="abe-fermentation"></a>

### acetone-butanol-ethanol fermentation

`abe-fermentation` &middot; fermentation &middot; target: propanone `acetone`

> Weizmann; cordite acetone

**Primary feedstocks** (1)

- D-glucose `glucose`

**Intermediates** (0)

- *(none: a single-step route has no intermediate by definition)*

**Products and byproducts** (5)

- 1-butanol `1-butanol`
- propanone `acetone`
- carbon dioxide `carbon-dioxide`
- ethanol `ethanol`
- hydrogen `hydrogen`

| # | step | in | out | conditions | class |
|--:|---|---|---|---|---|
| 1 | clostridial fermentation | glucose | acetone + 1-butanol + ethanol + carbon-dioxide + hydrogen | Clostridium acetobutylicum, 310 K | `fermentation` |

<a id="citric-acid-fermentation"></a>

### citric acid by fermentation

`citric-acid-fermentation` &middot; fermentation &middot; target: citric acid `citric-acid`

> Aspergillus niger

**Primary feedstocks** (4)

- calcium hydroxide `calcium-hydroxide`
- dioxygen `oxygen`
- sucrose `sucrose`
- sulfuric acid `sulfuric-acid`

**Intermediates** (2)

- calcium citrate `calcium-citrate`
- citric acid `citric-acid`

**Products and byproducts** (2)

- calcium sulfate `calcium-sulfate`
- water `water`

| # | step | in | out | conditions | class |
|--:|---|---|---|---|---|
| 1 | mould fermentation | sucrose + oxygen | citric-acid + water | Aspergillus niger, pH 2, 300 K | `fermentation` |
| 2 | recovery as the calcium salt | citric-acid + calcium-hydroxide | calcium-citrate + water | lime precipitation | `precipitation` |
| 3 | acidification | calcium-citrate + sulfuric-acid | citric-acid + calcium-sulfate | filter off gypsum | `acid-displacement-precipitating` |

<a id="msg-route"></a>

### monosodium glutamate

`msg-route` &middot; food &middot; target: L-glutamic acid `glutamic-acid`

> fermentation of sugar

**Primary feedstocks** (4)

- ammonia `ammonia`
- D-glucose `glucose`
- dioxygen `oxygen`
- sodium hydroxide `sodium-hydroxide`

**Intermediates** (1)

- L-glutamic acid `glutamic-acid`

**Products and byproducts** (3)

- carbon dioxide `carbon-dioxide`
- monosodium glutamate `monosodium-glutamate`
- water `water`

| # | step | in | out | conditions | class |
|--:|---|---|---|---|---|
| 1 | glutamate fermentation | glucose + ammonia + oxygen | glutamic-acid + carbon-dioxide + water | Corynebacterium, biotin-limited | `fermentation` |
| 2 | neutralisation | glutamic-acid + sodium-hydroxide | monosodium-glutamate + water | pH 7 | `proton-transfer` |

<a id="furfural-route"></a>

### furfural from pentosans

`furfural-route` &middot; biomass &middot; target: 2-furaldehyde `furfural`

> bran and cobs with acid

**Primary feedstocks** (1)

- hydrogen `hydrogen`

**Intermediates** (3)

- furan `furan`
- 2-furaldehyde `furfural`
- water `water`

**Products and byproducts** (2)

- carbon monoxide `carbon-monoxide`
- tetrahydrofuran `tetrahydrofuran`

**Catalysts** (both sides of one step, net stoichiometry zero)

- nickel metal `nickel`
- palladium metal `palladium`
- sulfuric acid `sulfuric-acid`
- D-xylose `xylose`

| # | step | in | out | conditions | class |
|--:|---|---|---|---|---|
| 1 | pentosan hydrolysis | xylose + water | xylose | dilute H2SO4, 450 K steam | `hydrolysis` |
| 2 | triple dehydration | xylose + sulfuric-acid | furfural + water + sulfuric-acid | 450 K, steam stripped | `dehydration-cyclisation` |
| 3 | decarbonylation to furan | furfural + palladium | furan + carbon-monoxide + palladium | 470 K, Pd | `decarbonylation` |
| 4 | hydrogenation to THF | furan + hydrogen + nickel | tetrahydrofuran + nickel | 420 K, Ni | `arene-hydrogenation` |

<a id="vanillin-lignin"></a>

### vanillin from lignin

`vanillin-lignin` &middot; flavours &middot; target: 4-hydroxy-3-methoxybenzaldehyde `vanillin`

> sulfite liquor oxidation

**Primary feedstocks** (2)

- coniferyl alcohol `lignin-monomer-coniferyl`
- dioxygen `oxygen`

**Intermediates** (0)

- *(none: a single-step route has no intermediate by definition)*

**Products and byproducts** (2)

- 4-hydroxy-3-methoxybenzaldehyde `vanillin`
- water `water`

**Catalysts** (both sides of one step, net stoichiometry zero)

- sodium hydroxide `sodium-hydroxide`

| # | step | in | out | conditions | class |
|--:|---|---|---|---|---|
| 1 | alkaline oxidation of lignin | lignin-monomer-coniferyl + oxygen + sodium-hydroxide | vanillin + water + sodium-hydroxide | 440 K, sulfite liquor, air | `oxidative-cleavage` |

<a id="vanillin-guaiacol"></a>

### vanillin from guaiacol

`vanillin-guaiacol` &middot; flavours &middot; target: 4-hydroxy-3-methoxybenzaldehyde `vanillin`

> the Reimer-Tiemann and glyoxylic routes

**Primary feedstocks** (3)

- oxoacetic acid `glyoxylic-acid`
- 2-methoxyphenol `guaiacol`
- dioxygen `oxygen`

**Intermediates** (1)

- vanillylmandelic acid `vanillylmandelic-acid`

**Products and byproducts** (3)

- carbon dioxide `carbon-dioxide`
- 4-hydroxy-3-methoxybenzaldehyde `vanillin`
- water `water`

**Catalysts** (both sides of one step, net stoichiometry zero)

- sodium hydroxide `sodium-hydroxide`

| # | step | in | out | conditions | class |
|--:|---|---|---|---|---|
| 1 | glyoxylic acid condensation | guaiacol + glyoxylic-acid + sodium-hydroxide | vanillylmandelic-acid + sodium-hydroxide | 310 K, alkaline | `electrophilic-hydroxyalkylation` |
| 2 | oxidative decarboxylation | vanillylmandelic-acid + oxygen | vanillin + carbon-dioxide + water | air, CuO, alkaline | `oxidative-decarboxylation` |

<a id="camphor-route"></a>

### synthetic camphor from pinene

`camphor-route` &middot; fine-chemicals &middot; target: camphor `camphor`

> turpentine to camphene to camphor

**Primary feedstocks** (4)

- ethanoic acid `acetic-acid`
- alpha-pinene `alpha-pinene`
- dioxygen `oxygen`
- sodium hydroxide `sodium-hydroxide`

**Intermediates** (3)

- borneol `borneol`
- camphene `camphene`
- isobornyl acetate `isobornyl-acetate`

**Products and byproducts** (3)

- camphor `camphor`
- sodium acetate `sodium-acetate`
- water `water`

**Catalysts** (both sides of one step, net stoichiometry zero)

- copper metal `copper`
- sulfuric acid `sulfuric-acid`
- titanium dioxide `titanium-dioxide`

| # | step | in | out | conditions | class |
|--:|---|---|---|---|---|
| 1 | pinene isomerisation | alpha-pinene + titanium-dioxide | camphene + titanium-dioxide | 430 K, TiO2 | `skeletal-isomerisation` |
| 2 | acetate addition | camphene + acetic-acid + sulfuric-acid | isobornyl-acetate + sulfuric-acid | 340 K | `markovnikov-addition` |
| 3 | saponification | isobornyl-acetate + sodium-hydroxide | borneol + sodium-acetate | reflux | `ester-hydrolysis` |
| 4 | oxidation | borneol + oxygen + copper | camphor + water + copper | dehydrogenation, 570 K | `alcohol-oxidation` |

<a id="vitamin-c-reichstein"></a>

### Reichstein vitamin C synthesis

`vitamin-c-reichstein` &middot; pharma &middot; target: L-ascorbic acid `ascorbic-acid`

> glucose, sorbitol, fermentation, lactonisation

**Primary feedstocks** (5)

- D-glucose `glucose`
- hydrogen `hydrogen`
- hydrogen chloride `hydrogen-chloride`
- dioxygen `oxygen`
- potassium permanganate `potassium-permanganate`

**Intermediates** (5)

- propanone `acetone`
- diacetone-2-keto-L-gulonic acid `diacetone-ketogulonic-acid`
- diacetone-L-sorbose `diacetone-sorbose`
- D-sorbitol `sorbitol`
- L-sorbose `sorbose`

**Products and byproducts** (1)

- L-ascorbic acid `ascorbic-acid`

**Catalysts** (both sides of one step, net stoichiometry zero)

- nickel metal `nickel`
- sulfuric acid `sulfuric-acid`
- water `water`

| # | step | in | out | conditions | class |
|--:|---|---|---|---|---|
| 1 | glucose hydrogenation | glucose + hydrogen + nickel | sorbitol + nickel | 420 K, 100 bar | `carbonyl-hydrogenation` |
| 2 | microbial oxidation | sorbitol + oxygen | sorbose + water | Acetobacter, 300 K | `biological-oxidation` |
| 3 | acetonide protection | sorbose + acetone + sulfuric-acid | diacetone-sorbose + water + sulfuric-acid | acid, ambient | `acetal-formation` |
| 4 | oxidation | diacetone-sorbose + potassium-permanganate | diacetone-ketogulonic-acid | alkaline, 310 K | `permanganate-alcohol-oxidation` |
| 5 | deprotection and lactonisation | diacetone-ketogulonic-acid + water + hydrogen-chloride | ascorbic-acid + acetone + water | acid, reflux | `hydrolysis-lactonisation` |

<a id="grignard-route"></a>

### Grignard addition to a carbonyl

`grignard-route` &middot; fine-chemicals &middot; target: 1-phenylethanol `1-phenylethanol`

> the organometallic workhorse

**Primary feedstocks** (4)

- ethanal `acetaldehyde`
- bromobenzene `bromobenzene`
- magnesium metal `magnesium`
- water `water`

**Intermediates** (2)

- phenylmagnesium bromide `grignard-phenylmagnesium-bromide`
- 1-phenylethanolate magnesium bromide `phenylethanolate-magnesium-bromide`

**Products and byproducts** (2)

- 1-phenylethanol `1-phenylethanol`
- magnesium hydroxide `magnesium-hydroxide`

| # | step | in | out | conditions | class |
|--:|---|---|---|---|---|
| 1 | reagent formation | bromobenzene + magnesium | grignard-phenylmagnesium-bromide | dry diethyl ether, reflux | `oxidative-insertion` |
| 2 | carbonyl addition | grignard-phenylmagnesium-bromide + acetaldehyde | phenylethanolate-magnesium-bromide | 273 K, ether | `nucleophilic-addition` |
| 3 | aqueous workup | phenylethanolate-magnesium-bromide + water | 1-phenylethanol + magnesium-hydroxide | dilute acid quench | `hydrolysis` |

<a id="wittig-route"></a>

### Wittig olefination

`wittig-route` &middot; fine-chemicals &middot; target: styrene `styrene`

> phosphonium ylide plus aldehyde

**Primary feedstocks** (4)

- benzaldehyde `benzaldehyde`
- iodomethane `iodomethane`
- n-butyllithium `n-butyllithium`
- triphenylphosphine `triphenylphosphine`

**Intermediates** (2)

- methyltriphenylphosphonium iodide `methyltriphenylphosphonium-iodide`
- methylenetriphenylphosphorane `ylide-methylenetriphenylphosphorane`

**Products and byproducts** (3)

- n-butane `butane`
- styrene `styrene`
- triphenylphosphine oxide `triphenylphosphine-oxide`

| # | step | in | out | conditions | class |
|--:|---|---|---|---|---|
| 1 | phosphonium salt | triphenylphosphine + iodomethane | methyltriphenylphosphonium-iodide | toluene, reflux | `nucleophilic-substitution` |
| 2 | ylide generation | methyltriphenylphosphonium-iodide + n-butyllithium | ylide-methylenetriphenylphosphorane + butane | THF, 195 K | `carbanion-generation` |
| 3 | olefination | ylide-methylenetriphenylphosphorane + benzaldehyde | styrene + triphenylphosphine-oxide | THF, warming to ambient | `wittig-olefination` |

<a id="diels-alder-route"></a>

### Diels-Alder cycloaddition

`diels-alder-route` &middot; fine-chemicals &middot; target: bicyclo[2.2.1]heptane `norbornane`

> butadiene or cyclopentadiene plus dienophile

**Primary feedstocks** (5)

- 1,3-butadiene `1,3-butadiene`
- 1,3-cyclopentadiene `cyclopentadiene`
- ethene `ethylene`
- hydrogen `hydrogen`
- maleic anhydride `maleic-anhydride`

**Intermediates** (1)

- bicyclo[2.2.1]hept-5-ene-2,3-dicarboxylic anhydride `norbornene-dicarboxylic-anhydride`

**Products and byproducts** (2)

- cyclohexene `cyclohexene`
- bicyclo[2.2.1]heptane `norbornane`

**Catalysts** (both sides of one step, net stoichiometry zero)

- palladium metal `palladium`

| # | step | in | out | conditions | class |
|--:|---|---|---|---|---|
| 1 | cycloaddition | 1,3-butadiene + ethylene | cyclohexene | 470 K, 20 bar | `diels-alder-cycloaddition` |
| 2 | maleic anhydride adduct | cyclopentadiene + maleic-anhydride | norbornene-dicarboxylic-anhydride | 273 K, ethyl acetate | `diels-alder-cycloaddition` |
| 3 | hydrogenation of the adduct | norbornene-dicarboxylic-anhydride + hydrogen + palladium | norbornane + palladium | H2, Pd/C | `alkene-hydrogenation` |

<a id="mannich-route"></a>

### Mannich reaction

`mannich-route` &middot; fine-chemicals &middot; target: 4-dimethylamino-2-butanone `4-dimethylamino-2-butanone`

> amine, formaldehyde and an enolisable ketone

**Primary feedstocks** (4)

- propanone `acetone`
- dimethylamine `dimethylamine`
- methanal `formaldehyde`
- hydrogen chloride `hydrogen-chloride`

**Intermediates** (1)

- dimethylmethyleneiminium `dimethylmethyleneiminium`

**Products and byproducts** (3)

- 4-dimethylamino-2-butanone `4-dimethylamino-2-butanone`
- hydronium ion `hydronium`
- water `water`

| # | step | in | out | conditions | class |
|--:|---|---|---|---|---|
| 1 | iminium formation | dimethylamine + formaldehyde + hydrogen-chloride | dimethylmethyleneiminium + water | aqueous acid | `iminium-formation` |
| 2 | enol attack | dimethylmethyleneiminium + acetone | 4-dimethylamino-2-butanone + hydronium | ethanol, reflux | `mannich-reaction` |

<a id="michael-robinson"></a>

### Michael addition and Robinson annulation

`michael-robinson` &middot; fine-chemicals &middot; target: isophorone `isophorone`

> conjugate addition then intramolecular aldol

**Primary feedstocks** (2)

- propanone `acetone`
- 3-buten-2-one `methyl-vinyl-ketone`

**Intermediates** (1)

- 2,6-heptanedione `2,6-heptanedione`

**Products and byproducts** (2)

- isophorone `isophorone`
- water `water`

**Catalysts** (both sides of one step, net stoichiometry zero)

- sodium hydroxide `sodium-hydroxide`

| # | step | in | out | conditions | class |
|--:|---|---|---|---|---|
| 1 | Michael addition | acetone + methyl-vinyl-ketone + sodium-hydroxide | 2,6-heptanedione + sodium-hydroxide | base, 300 K | `michael-addition` |
| 2 | intramolecular aldol | 2,6-heptanedione + sodium-hydroxide | isophorone + water + sodium-hydroxide | base, reflux | `intramolecular-aldol` |

## modern

<a id="biodiesel-route"></a>

### biodiesel by transesterification

`biodiesel-route` &middot; fuels &middot; target: methyl oleate `methyl-oleate`

> glycerol co-product

**Primary feedstocks** (2)

- methanol `methanol`
- glyceryl trioleate `triolein`

**Intermediates** (0)

- *(none: a single-step route has no intermediate by definition)*

**Products and byproducts** (2)

- 1,2,3-propanetriol `glycerol`
- methyl oleate `methyl-oleate`

**Catalysts** (both sides of one step, net stoichiometry zero)

- sodium methoxide `sodium-methoxide`

| # | step | in | out | conditions | class |
|--:|---|---|---|---|---|
| 1 | transesterification | triolein + methanol + sodium-methoxide | methyl-oleate + glycerol + sodium-methoxide | 330 K, 1% NaOMe | `transesterification` |

<a id="glycerol-epichlorohydrin"></a>

### glycerol to epichlorohydrin

`glycerol-epichlorohydrin` &middot; polymers &middot; target: epichlorohydrin `epichlorohydrin`

> biodiesel glycerol valorisation

**Primary feedstocks** (3)

- 1,2,3-propanetriol `glycerol`
- hydrogen chloride `hydrogen-chloride`
- sodium hydroxide `sodium-hydroxide`

**Intermediates** (1)

- 1,3-dichloro-2-propanol `1,3-dichloro-2-propanol`

**Products and byproducts** (3)

- epichlorohydrin `epichlorohydrin`
- sodium chloride `sodium-chloride`
- water `water`

**Catalysts** (both sides of one step, net stoichiometry zero)

- ethanoic acid `acetic-acid`

| # | step | in | out | conditions | class |
|--:|---|---|---|---|---|
| 1 | hydrochlorination | glycerol + hydrogen-chloride + acetic-acid | 1,3-dichloro-2-propanol + water + acetic-acid | 380 K, carboxylic acid catalyst | `nucleophilic-substitution` |
| 2 | ring closure | 1,3-dichloro-2-propanol + sodium-hydroxide | epichlorohydrin + sodium-chloride + water | caustic, 340 K | `intramolecular-williamson` |

<a id="lactic-acid-pla"></a>

### lactic acid to polylactide

`lactic-acid-pla` &middot; polymers &middot; target: polylactic acid repeat unit `pla-unit`

> fermentation, lactide, ring-opening

**Primary feedstocks** (1)

- D-glucose `glucose`

**Intermediates** (3)

- 2-hydroxypropanoic acid `lactic-acid`
- *lactic-oligomer-marker* (no molecular graph)
- L-lactide `lactide`

**Products and byproducts** (2)

- polylactic acid repeat unit `pla-unit`
- water `water`

**Catalysts** (both sides of one step, net stoichiometry zero)

- tin(IV) chloride `tin-iv-chloride`

| # | step | in | out | conditions | class |
|--:|---|---|---|---|---|
| 1 | lactic fermentation | glucose | lactic-acid | Lactobacillus, 320 K | `fermentation` |
| 2 | oligomerisation | lactic-acid | lactic-oligomer-marker + water | 470 K, vacuum | `polycondensation` |
| 3 | depolymerisation to lactide | lactic-oligomer-marker + tin-iv-chloride | lactide + tin-iv-chloride | 500 K, vacuum, Sn octoate | `depolymerisation` |
| 4 | ring-opening polymerisation | lactide + tin-iv-chloride | pla-unit + tin-iv-chloride | 460 K, melt ROP | `ring-opening-polymerisation` |

<a id="hmf-route"></a>

### HMF from fructose

`hmf-route` &middot; biomass &middot; target: 5-HMF `5-hydroxymethylfurfural`

> the biomass platform molecule

**Primary feedstocks** (1)

- D-fructose `fructose`

**Intermediates** (2)

- 5-HMF `5-hydroxymethylfurfural`
- water `water`

**Products and byproducts** (2)

- methanoic acid `formic-acid`
- 4-oxopentanoic acid `levulinic-acid`

**Catalysts** (both sides of one step, net stoichiometry zero)

- sulfuric acid `sulfuric-acid`

| # | step | in | out | conditions | class |
|--:|---|---|---|---|---|
| 1 | fructose dehydration | fructose + sulfuric-acid | 5-hydroxymethylfurfural + water + sulfuric-acid | 420 K, DMSO or biphasic | `dehydration-cyclisation` |
| 2 | rehydration byproduct | 5-hydroxymethylfurfural + water + sulfuric-acid | levulinic-acid + formic-acid + sulfuric-acid | the side reaction that limits yield | `hydration-ring-opening` |

<a id="menthol-route"></a>

### menthol from citronellal

`menthol-route` &middot; flavours &middot; target: L-menthol `menthol`

> asymmetric isomerisation then cyclisation

**Primary feedstocks** (2)

- citronellal `citronellal`
- hydrogen `hydrogen`

**Intermediates** (1)

- isopulegol `isopulegol`

**Products and byproducts** (1)

- L-menthol `menthol`

**Catalysts** (both sides of one step, net stoichiometry zero)

- nickel metal `nickel`
- zinc chloride `zinc-chloride`

| # | step | in | out | conditions | class |
|--:|---|---|---|---|---|
| 1 | citronellal cyclisation | citronellal + zinc-chloride | isopulegol + zinc-chloride | ene reaction, 270 K, ZnBr2 | `carbonyl-ene-cyclisation` |
| 2 | hydrogenation | isopulegol + hydrogen + nickel | menthol + nickel | 350 K, Raney Ni | `alkene-hydrogenation` |

## Reaction classes used, by frequency

This is the list a template library has to grow into. `validation/catalog_coverage.py` reports which of them exist today.

| class | steps | routes |
|---|---:|---:|
| proton-transfer | 11 | 9 |
| hydrolysis | 8 | 8 |
| combustion | 6 | 6 |
| glycoside-hydrolysis | 6 | 5 |
| radical-polymerisation | 6 | 6 |
| nucleophilic-substitution | 6 | 6 |
| carbothermic-reduction | 5 | 5 |
| precipitation-metathesis | 5 | 5 |
| electrophilic-aromatic-nitration | 5 | 3 |
| polycondensation | 5 | 5 |
| fermentation | 5 | 5 |
| ester-hydrolysis | 5 | 5 |
| carbanion-generation | 5 | 5 |
| roasting | 4 | 4 |
| electrolysis | 4 | 4 |
| ammoxidation | 4 | 2 |
| gas-solid-reduction | 4 | 3 |
| electrophilic-aromatic-sulfonation | 4 | 4 |
| nucleophilic-addition | 4 | 4 |
| catalytic-air-oxidation | 4 | 3 |
| gas-phase-oxidation | 3 | 3 |
| catalytic-gas-oxidation | 3 | 3 |
| calcination | 3 | 3 |
| catalytic-gas-synthesis | 3 | 2 |
| acid-displacement-precipitating | 3 | 3 |
| formulation | 3 | 3 |
| esterification-nitration | 3 | 3 |
| pyrolysis | 3 | 3 |
| nitro-hydrogenation | 3 | 3 |
| alkali-fusion | 3 | 3 |
| diazotisation | 3 | 3 |
| friedel-crafts-hydroxyalkylation | 3 | 3 |
| n-acylation | 3 | 3 |
| williamson-ether-synthesis | 3 | 3 |
| alcohol-oxidation | 3 | 3 |
| intramolecular-williamson | 3 | 3 |
| esterification | 3 | 3 |
| alkene-hydrogenation | 3 | 3 |
| isomerisation | 3 | 3 |
| lime-slaking | 2 | 2 |
| disproportionation-hydrolysis | 2 | 2 |
| halide-oxidation | 2 | 2 |
| oxidative-dissolution | 2 | 2 |
| disproportionation | 2 | 2 |
| precipitation | 2 | 2 |
| condensation | 2 | 2 |
| dissolving-metal-reduction | 2 | 2 |
| oxidative-dimerisation | 2 | 2 |
| azo-coupling | 2 | 2 |
| leuco-dye-oxidation | 2 | 2 |
| friedel-crafts-alkylation | 2 | 2 |
| autoxidation | 2 | 2 |
| aldehyde-oxidation | 2 | 2 |
| amide-hydrolysis | 2 | 2 |
| swarts-halogen-exchange | 2 | 2 |
| halohydrin-formation | 2 | 2 |
| epoxide-alkoxylation | 2 | 1 |
| transesterification | 2 | 2 |
| nitric-acid-oxidation | 2 | 1 |
| oxime-formation | 2 | 2 |
| beckmann-rearrangement | 2 | 2 |
| ring-opening-polymerisation | 2 | 2 |
| electro-organic-coupling | 2 | 2 |
| phosgenation | 2 | 2 |
| crosslinking | 2 | 2 |
| hydroformylation | 2 | 1 |
| decarboxylation | 2 | 2 |
| biological-transformation | 2 | 2 |
| dehydration-cyclisation | 2 | 2 |
| oxidative-cleavage | 2 | 2 |
| diels-alder-cycloaddition | 2 | 1 |
| dehydration | 2 | 2 |
| isocyanate-hydrolysis | 2 | 2 |
| metal-ion-aldehyde-oxidation | 2 | 2 |
| redox-oxygen-transfer | 1 | 1 |
| nitrosation | 1 | 1 |
| acid-anhydride-absorption | 1 | 1 |
| sulfate-thermal-decomposition | 1 | 1 |
| comproportionation | 1 | 1 |
| salt-metathesis | 1 | 1 |
| dissolution | 1 | 1 |
| carbonate-equilibrium | 1 | 1 |
| bicarbonate-thermal-decomposition | 1 | 1 |
| solid-carbonation | 1 | 1 |
| thermal-fixation | 1 | 1 |
| acid-displacement | 1 | 1 |
| gas-solid-fixation | 1 | 1 |
| amphoteric-dissolution | 1 | 1 |
| boudouard | 1 | 1 |
| slagging | 1 | 1 |
| roasting-to-metal | 1 | 1 |
| metallothermic-reduction | 1 | 1 |
| deflagration | 1 | 1 |
| ipso-nitrodesulfonation | 1 | 1 |
| nitrolysis | 1 | 1 |
| aldol-cannizzaro | 1 | 1 |
| oxidative-nitrosation | 1 | 1 |
| separation | 1 | 1 |
| nitronium-generation | 1 | 1 |
| electrophilic-aromatic-substitution | 1 | 1 |
| arenium-deprotonation | 1 | 1 |
| oxidative-coupling | 1 | 1 |
| arene-oxidation-to-quinone | 1 | 1 |
| side-chain-oxidation | 1 | 1 |
| aldol-cyclisation | 1 | 1 |
| n-alkylation | 1 | 1 |
| pyrolytic-synthesis | 1 | 1 |
| basic-carbonate-precipitation | 1 | 1 |
| direct-combination | 1 | 1 |
| hock-rearrangement | 1 | 1 |
| electrophilic-aromatic-halogenation | 1 | 1 |
| nucleophilic-aromatic-substitution | 1 | 1 |
| electrophilic-hydroxymethylation | 1 | 1 |
| kolbe-schmitt-carboxylation | 1 | 1 |
| acylation-esterification | 1 | 1 |
| crystallisation | 1 | 1 |
| nitro-partial-hydrogenation | 1 | 1 |
| bamberger-rearrangement | 1 | 1 |
| sulfonamide-formation | 1 | 1 |
| amide-coupling | 1 | 1 |
| haloform | 1 | 1 |
| radical-halogenation | 1 | 1 |
| carbonyl-hydration | 1 | 1 |
| steam-reforming | 1 | 1 |
| water-gas-shift | 1 | 1 |
| fischer-tropsch | 1 | 1 |
| carbonylation | 1 | 1 |
| pyrolysis-dehydration | 1 | 1 |
| wacker-oxidation | 1 | 1 |
| alkyne-hydration | 1 | 1 |
| thermal-cracking | 1 | 1 |
| catalytic-epoxidation | 1 | 1 |
| epoxide-hydrolysis | 1 | 1 |
| nitrile-hydrogenation | 1 | 1 |
| halogen-addition | 1 | 1 |
| oxychlorination | 1 | 1 |
| dehydrohalogenation | 1 | 1 |
| catalytic-dehydrogenation | 1 | 1 |
| coordination-polymerisation | 1 | 1 |
| cyanohydrin-formation | 1 | 1 |
| ritter-type-hydration | 1 | 1 |
| interfacial-polycondensation | 1 | 1 |
| allylic-chlorination | 1 | 1 |
| polyaddition | 1 | 1 |
| urea-deammoniation | 1 | 1 |
| trimerisation | 1 | 1 |
| direct-process | 1 | 1 |
| hydrolysis-condensation | 1 | 1 |
| equilibration | 1 | 1 |
| alkyne-dimerisation | 1 | 1 |
| hydrohalogenation | 1 | 1 |
| dehydration-dehydrogenation | 1 | 1 |
| radical-copolymerisation | 1 | 1 |
| polysaccharide-alkoxide | 1 | 1 |
| xanthation | 1 | 1 |
| regeneration | 1 | 1 |
| aldol-condensation | 1 | 1 |
| enal-hydrogenation | 1 | 1 |
| saponification | 1 | 1 |
| salting-out | 1 | 1 |
| glycolysis | 1 | 1 |
| biological-reduction | 1 | 1 |
| alkene-hydration | 1 | 1 |
| ether-condensation | 1 | 1 |
| depolymerisation | 1 | 1 |
| decarbonylation | 1 | 1 |
| arene-hydrogenation | 1 | 1 |
| hydration-ring-opening | 1 | 1 |
| alkene-isomerisation | 1 | 1 |
| electrophilic-hydroxyalkylation | 1 | 1 |
| oxidative-decarboxylation | 1 | 1 |
| skeletal-isomerisation | 1 | 1 |
| markovnikov-addition | 1 | 1 |
| carbonyl-ene-cyclisation | 1 | 1 |
| reduction | 1 | 1 |
| oxidative-complexation | 1 | 1 |
| photoreduction | 1 | 1 |
| chemical-reduction | 1 | 1 |
| complexation-dissolution | 1 | 1 |
| carbonyl-hydrogenation | 1 | 1 |
| biological-oxidation | 1 | 1 |
| acetal-formation | 1 | 1 |
| permanganate-alcohol-oxidation | 1 | 1 |
| hydrolysis-lactonisation | 1 | 1 |
| imine-formation | 1 | 1 |
| nitrile-hydrolysis | 1 | 1 |
| imide-deprotonation | 1 | 1 |
| hydrazinolysis | 1 | 1 |
| ester-hydrolysis-decarboxylation | 1 | 1 |
| oxidative-insertion | 1 | 1 |
| wittig-olefination | 1 | 1 |
| aldol-addition | 1 | 1 |
| claisen-condensation | 1 | 1 |
| lewis-acid-activation | 1 | 1 |
| friedel-crafts-acylation | 1 | 1 |
| cannizzaro-disproportionation | 1 | 1 |
| perkin-condensation | 1 | 1 |
| knoevenagel-doebner-condensation | 1 | 1 |
| n-halogenation | 1 | 1 |
| hofmann-rearrangement | 1 | 1 |
| nucleophilic-acyl-substitution | 1 | 1 |
| curtius-rearrangement | 1 | 1 |
| sandmeyer-substitution | 1 | 1 |
| alpha-elimination | 1 | 1 |
| electrophilic-formylation | 1 | 1 |
| hydrazone-formation | 1 | 1 |
| fischer-indolisation | 1 | 1 |
| skraup-cyclisation | 1 | 1 |
| multicomponent-condensation | 1 | 1 |
| oxidative-aromatisation | 1 | 1 |
| iminium-formation | 1 | 1 |
| mannich-reaction | 1 | 1 |
| michael-addition | 1 | 1 |
| intramolecular-aldol | 1 | 1 |
| alpha-halogenation | 1 | 1 |
| haloform-cleavage | 1 | 1 |
| hydride-thermal-deposition | 1 | 1 |
| oxidative-digestion | 1 | 1 |


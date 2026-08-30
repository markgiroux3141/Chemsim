-- Turn pandoc fenced divs into the LaTeX callout environments defined in
-- preamble.tex, so that markdown INSIDE a callout is still markdown.
--
--     ::: {.keypoint title="Detailed balance"}
--     Text, *emphasis*, lists -- all processed normally.
--     :::
--
-- Recognised classes: keypoint, physics, trap, aside.
--
-- The title is a plain attribute string, so it reaches LaTeX unprocessed and
-- has to be escaped here. Several titles in this manual legitimately contain
-- underscores (`jac_sparsity`, `conservation_report`) and percent signs.

local ENVS = { keypoint = true, physics = true, trap = true, aside = true }

local function tex_escape(s)
  s = s:gsub("\\", "\\textbackslash{}")
  s = s:gsub("([&%%%$#_{}])", "\\%1")
  s = s:gsub("~", "\\textasciitilde{}")
  s = s:gsub("%^", "\\textasciicircum{}")
  return s
end

function Div(el)
  for _, cls in ipairs(el.classes) do
    if ENVS[cls] then
      local title = el.attributes["title"]
      local open = "\\begin{" .. cls .. "}"
      if title and title ~= "" then
        open = open .. "[" .. tex_escape(title) .. "]"
      end
      local blocks = { pandoc.RawBlock("latex", open) }
      for _, b in ipairs(el.content) do
        table.insert(blocks, b)
      end
      table.insert(blocks, pandoc.RawBlock("latex", "\\end{" .. cls .. "}"))
      return blocks
    end
  end
  return el
end

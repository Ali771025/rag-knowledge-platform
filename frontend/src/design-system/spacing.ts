export const dsSpacing = {
  0: "0rem",
  1: "0.25rem",
  2: "0.5rem",
  3: "0.75rem",
  4: "1rem",
  5: "1.25rem",
  6: "1.5rem",
  7: "1.75rem",
  8: "2rem",
  10: "2.5rem",
  12: "3rem",
  16: "4rem"
} as const;

export const dsLayoutRhythm = {
  stackGapSm: dsSpacing[2],
  stackGapMd: dsSpacing[3],
  stackGapLg: dsSpacing[4],
  sectionGap: dsSpacing[6],
  panelPadding: dsSpacing[3],
  cardPadding: dsSpacing[3],
  inputPadding: dsSpacing[3]
} as const;

export const dsChatSpacing = {
  messageGap: dsSpacing[3],
  panelGap: dsSpacing[3],
  inputTopGap: dsSpacing[3],
  actionGap: dsSpacing[2]
} as const;

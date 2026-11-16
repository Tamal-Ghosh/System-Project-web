/** Values must match the checkpoint recipe's site vocabulary. */
export const lesionLocations = [
  { value: 'unknown', label: 'Unknown' },
  { value: 'foot', label: 'Foot' },
  { value: 'genital', label: 'Genital' },
  { value: 'hand', label: 'Hand' },
  { value: 'head_neck_face', label: 'Head / neck / face' },
  { value: 'lower_extremity', label: 'Lower extremity' },
  { value: 'trunk', label: 'Trunk (chest / back / abdomen)' },
  { value: 'upper_extremity', label: 'Upper extremity' },
] as const

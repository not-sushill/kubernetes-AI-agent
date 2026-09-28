const collator = new Intl.Collator("en", { numeric: true, sensitivity: "base" });
function numberValue(value: string): number | null {
  if (/^-?\d+(\.\d+)?%?$/.test(value)) return Number(value.replace("%", ""));
  const ratio = value.match(/^(\d+)\/(\d+)$/);
  if (ratio) return Number(ratio[1]) / Math.max(Number(ratio[2]), 1);
  const duration = value.match(/^(?:(\d+)d)?(?:(\d+)h)?(?:(\d+)m)?(?:(\d+)s)?$/);
  if (duration && value) return Number(duration[1]||0)*86400+Number(duration[2]||0)*3600+Number(duration[3]||0)*60+Number(duration[4]||0);
  if (/^\d{4}-\d{2}-\d{2}T|^\d{1,2} [A-Za-z]+ \d{4}/.test(value)) {
    const date = Date.parse(value.replace(/ IST$/, " GMT+0530").replace(" at ", " "));
    if (Number.isFinite(date)) return date;
  }
  return null;
}
export function compareTableValues(left: string, right: string): number {
  const a = left.trim(), b = right.trim();
  const an = numberValue(a), bn = numberValue(b);
  if(an !== null && bn !== null) return an - bn;
  return collator.compare(a,b);
}

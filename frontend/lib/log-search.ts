export function istLogStart(value:string):string {
  if (!/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}$/.test(value)) throw new Error("Choose a valid start date and time in IST.");
  const date=new Date(`${value}:00+05:30`);
  if (!Number.isFinite(date.getTime()) || new Date(date.getTime()+19800000).toISOString().slice(0,16)!==value) throw new Error("Invalid IST start time.");
  return date.toISOString();
}
export function searchLogs(lines:string[],query:string,errorsOnly:boolean,caseSensitive:boolean,context:number) {
  const needle=caseSensitive ? query : query.toLowerCase();
  const matches:number[]=[];const shown=new Set<number>();
  lines.forEach((line,i)=>{
    if (!(caseSensitive ? line : line.toLowerCase()).includes(needle)) return;
    if (errorsOnly && !/\b(error|exception|fatal|panic|failed|failure)\b/i.test(line)) return;
    matches.push(i);
    for(let n=Math.max(0,i-context);n<=Math.min(lines.length-1,i+context);n++)shown.add(n);
  });
  return {matches, rows:[...shown].sort((a,b)=>a-b).map(i=>({number:i+1,line:lines[i]}))};
}

export function logOptionsForTarget(target:string, selection:{target:string; options:import("@/hooks/use-kubernetes").LogOptions}):import("@/hooks/use-kubernetes").LogOptions {
  return target === selection.target ? selection.options : {tail:5000,previous:false};
}

// Return text segments, never HTML: log content remains escaped by React.
export function highlightLogText(line:string, query:string, caseSensitive:boolean, errorsOnly:boolean) {
  const ranges:{start:number;end:number}[]=[];
  if(query) {
    const escaped=query.replace(/[.*+?^${}()|[\]\\]/g,"\\$&");
    const pattern=new RegExp(escaped,caseSensitive ? "g" : "gi");
    for(const match of line.matchAll(pattern)) ranges.push({start:match.index!,end:match.index!+match[0].length});
  }
  if(errorsOnly) for(const match of line.matchAll(/\b(error|exception|fatal|panic|failed|failure)\b/gi)) ranges.push({start:match.index!,end:match.index!+match[0].length});
  ranges.sort((a,b)=>a.start-b.start);
  const merged:{start:number;end:number}[]=[];
  for(const range of ranges){const last=merged[merged.length-1];if(last && range.start<=last.end)last.end=Math.max(last.end,range.end);else merged.push({...range});}
  const parts:{text:string;highlight:boolean}[]=[];let cursor=0;
  for(const range of merged){if(range.start>cursor)parts.push({text:line.slice(cursor,range.start),highlight:false});parts.push({text:line.slice(range.start,range.end),highlight:true});cursor=range.end;}
  if(cursor<line.length)parts.push({text:line.slice(cursor),highlight:false});
  return parts;
}

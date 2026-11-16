"""Read only explicit times/locations from the official notice, without inference."""
import re

TIME=re.compile(r'(?:nga|prej)\s+or(?:a|[eë]s)\s+(\d{1,2}[:.]\d{2})\s*(?:deri(?:\s+n[eë])?(?:\s+or(?:a|[eë]n))?\s*|[-–]\s*)(\d{1,2}[:.]\d{2})',re.I)


def parse_outages(text):
    matches=list(TIME.finditer(text));outages=[]
    for index,match in enumerate(matches):
        times=[value.replace('.',':') for value in match.groups()]
        if any(int(value.split(':')[0])>23 or int(value.split(':')[1])>59 for value in times):continue
        following=text[match.end():matches[index+1].start() if index+1<len(matches) else len(text)]
        places=re.search(r'Vendet(?:\s+pa\s+energji)?\s*:\s*(.*?)(?=\s*Arsye(?:ja)?\s*:|\bNga\s+(?:TS|NS)\b|$)',following,re.I|re.S)
        reason=re.search(r'Arsye(?:ja)?\s*:\s*(.*?)(?=\bNga\s+(?:TS|NS)\b|$)',following,re.I|re.S)
        outages.append(dict(start=times[0].zfill(5),end=times[1].zfill(5),
                            locations=' '.join(places[1].split()) if places else '',
                            reason=' '.join(reason[1].split()) if reason else ''))
    return outages

(async()=>{try{
 const base='d8173a48cd35cd99d483de91787e04014cf498b8';
 const response=await fetch('https://api.github.com/repos/willandbeyond/bonch-test/compare/'+base+'...main',{headers:{Accept:'application/vnd.github+json'}});
 if(!response.ok)throw Error('Release metadata unavailable');
 const data=await response.json();
 const commits=data.commits||[];
 const latest=commits[commits.length-1];
 if(!latest)return;
 const version='0.5.'+data.total_commits;
 const timestamp=latest.commit?.committer?.date;
 if(!timestamp)return;
 document.querySelectorAll('.version-number').forEach(el=>el.textContent='V'+version);
 document.querySelectorAll('time.build-time').forEach(el=>{el.dateTime=timestamp;el.textContent=timestamp;});
 document.querySelectorAll('.version-history-current').forEach(el=>el.textContent='v'+version);
 document.querySelectorAll('.version-footer-current').forEach(el=>el.textContent='Version '+version);
 document.querySelectorAll('time.version-build-time').forEach(el=>{el.dateTime=timestamp;el.textContent=new Date(timestamp).toLocaleString('en-US',{timeZone:'America/New_York',year:'numeric',month:'short',day:'numeric',hour:'numeric',minute:'2-digit',timeZoneName:'short'});});
 }catch(e){console.warn('Using last known release metadata',e)}
})();
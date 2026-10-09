"use strict";
(()=>{const a=document.getElementById('shared-learn-action'),v=document.getElementById('shared-learn-view'),video=document.getElementById('shared-learn-video');function update(){video.pause();const stem='/media/learned-'+a.value+'-'+v.value;video.poster=stem+'-png.png';video.src=stem+'-mp4.mp4';video.load();}a.onchange=v.onchange=update;update();})();

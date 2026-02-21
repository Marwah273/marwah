document.addEventListener('DOMContentLoaded', function(){
  var btn = document.getElementById('copy-share');
  if (!btn) return;
  btn.addEventListener('click', function(e){
    e.preventDefault();
    var student = btn.getAttribute('data-student');
    var token = btn.getAttribute('data-token');
    var base = window.location.protocol + '//' + window.location.host + '/student/';
    var url = base + encodeURIComponent(student) + '?t=' + encodeURIComponent(token);
    // Use clipboard API when available
    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(url).then(function(){
        btn.textContent = 'Copied!';
        setTimeout(function(){ btn.textContent = 'Copy link'; }, 2000);
      }).catch(function(){ alert('Copy failed — please copy manually: ' + url); });
    } else {
      // Fallback: create temporary textarea
      var ta = document.createElement('textarea');
      ta.value = url;
      document.body.appendChild(ta);
      ta.select();
      try {
        document.execCommand('copy');
        btn.textContent = 'Copied!';
        setTimeout(function(){ btn.textContent = 'Copy link'; }, 2000);
      } catch (e) {
        alert('Please copy this link: ' + url);
      }
      document.body.removeChild(ta);
    }
  });
});

document.getElementById('permalink').addEventListener('click', function(e) {
	e.preventDefault();
	
	var dummy = document.createElement('input');
	dummy.value = this.href;

	document.body.appendChild(dummy);

	dummy.select();
	document.execCommand('copy');

	document.body.removeChild(dummy);
});
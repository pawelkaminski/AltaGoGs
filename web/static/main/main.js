$(document).ready(function () {

    $('.mover').click(function (e) {
        window.location.href = $(this).attr('url');
    });

    $('.mover').hover(function() {
        $(this).css('cursor','pointer');
    });

    $('.mover').hover( function() {
      var $this = $(this);
      $this.data('bgcolor', $this.css('background-color')).css('background-color', '#F8F6A6');
    }, function() {
      var $this = $(this);
      $this.css('background-color', $this.data('bgcolor'));
    }
  );
});

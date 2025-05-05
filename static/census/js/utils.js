var utils = (function (scope) {
    var hide = {};
    hide.el = function (element) {
        element.classList.add("hidden");
    };
    hide.id = function (id) {
        var element = document.getElementById(id);
        hide.el(element);
    };
    hide.cls = function (cls) {
        var elements = document.getElementsByClassName(cls);
        for (var i = 0; i < elements.length; i++) {
            hide.el(elements[i]);
        }
    };
    scope.hide = hide;

    var show = {};
    show.el = function (element) {
        element.classList.remove("hidden");
    };
    show.id = function (id) {
        var element = document.getElementById(id);
        show.el(element);
    };
    show.cls = function (cls) {
        var elements = document.getElementsByClassName(cls);
        for (var i = 0; i < elements.length; i++) {
            show.el(elements[i]);
        }
    };
    scope.show = show;

    var togglehide = {};
    togglehide.el = function (element) {
        if (element.classList.contains("hidden")) {
            show.el(element);
        } else {
            hide.el(element);
        }
    };
    togglehide.id = function (id) {
        var element = document.getElementById(id);
        togglehide.el(element);
    }
    togglehide.cls = function(cls) {
        var elements = document.getElementsByClassName(cls);
        for (var i = 0; i < elements.length; i++) {
            togglehide.el(elements[i]);
        }
    }
    scope.togglehide = togglehide;

    var get = {};
    get.id = function (id) {
        return document.getElementById(id);
    };
    get.cls = function (cls) {
        var result = [];
        var els = document.getElementsByClassName(cls);
        for (var i = 0; i < els.length; i++) {
            result.push(els[i]);
        }
        return result;
    };
    scope.get = get;

    return scope;
})(utils || {});


// ────────────────────────────────────────────────────────────────────────────
// Autocomplete for “location” field
// ────────────────────────────────────────────────────────────────────────────
$(function() {
    $("#location-input").autocomplete({
      minLength: 2,    // start suggesting after 2 chars
      delay: 200,      // wait 200ms
      source: function(request, response) {
        $.getJSON(
          "{% url 'autofill_location' %}" + encodeURIComponent(request.term) + "/",
          function(data) {
            response(data.matches);
          }
        );
      },
      select: function(event, ui) {
        // on select, fill input (and optionally submit)
        $("#location-input").val(ui.item.value);
        // $("#search-bar-form form").submit(); // uncomment to auto-submit
        return false;
      }
    });
  });
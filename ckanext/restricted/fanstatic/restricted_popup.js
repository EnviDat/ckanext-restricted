// Enable JavaScript's strict mode. Strict mode catches some common
// programming errors and throws exceptions, prevents some unsafe actions from
// being taken, and disables some confusing and bad JavaScript features.
"use strict";

ckan.module('restricted_popup', function ($) {
  return {
    initialize: function () {
      console.log("Initialize", this.el);
      this.el.popover({title: this.options.title,
                       content: this.options.content,
		       html: true,
                       placement: 'left'});
    }
  };
});

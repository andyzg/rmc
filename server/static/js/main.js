/**
 * Count how many times something is getting called, then display the result in
 * the console once the calls have slowed down.
 *
 * This is a reasonable alternative to console.trace() or console.count(), since
 * those both slow down the browser a ton if you've got 1000+ calls.
 *
 * Usage:
 *
 *  function somethingCool() {
 *    countMe("somethingCool");
 *    someStuff();
 *  };
 */
window.countMe = (function() {
  var count = {};
  var logger = {};
  return function(msg) {
    require(['ext/underscore'], function(_) {
      if (!logger[msg]) {
        logger[msg] = _.debounce(function() {
          console.log(msg, count[msg]);
        }, 100);
      }
      count[msg] = (count[msg] || 0) + 1;
      logger[msg]();
    });
  };
})();

require.config({
  shim: {
    'ext/backbone': {
      deps: ['ext/jquery', 'ext/underscore'],
      exports: 'Backbone'
    },
    // Not really needed since jQuery is already AMD-compliant, but just for
    // the sake of completeness
    'ext/jquery': {
      exports: '$'
    },
    'ext/jqueryui': {
      deps: ['ext/jquery']
    },
    'ext/bootstrap': {
      deps: ['ext/jquery']
    },
    'ext/select2': {
      deps: ['ext/jquery']
    },
    'ext/autosize': {
      deps: ['ext/jquery']
    },
    'ext/cookie': {
      deps: ['ext/jquery']
    },
    'ext/moment': {
      exports: 'moment'
    },
    'ext/slimScroll': {
      deps: ['ext/jquery', 'ext/jqueryui']
    },
    'ext/toastr': {
      deps: ['ext/jquery'],
      exports: 'toastr'
    },
    'ext/underscore': {
      exports: '_'
    },
    'ext/underscore.string': {
      deps: ['ext/underscore'],
      exports: function(_) {
        return _.string;
      }
    },
    'ext/validate': {
      deps: ['ext/jquery']
    },
    'ext/smartbanner': {
      deps:['ext/jquery'],
      exports: 'smartbanner'
    }
  },

  baseUrl: '/static/js/',

  paths: {
    'ext/backbone': 'ext/backbone-0.9.2',
    'ext/jquery': 'ext/jquery-1.8.1',
    'ext/bootstrap': 'ext/bootstrap-2.1.1',
    'ext/select2': 'ext/select2.min',
    'ext/autosize': 'ext/jquery.autosize',
    'ext/cookie': 'ext/jquery.cookie',
    'ext/slimScroll': 'ext/slimScroll-0.6.0',
    'ext/jqueryui': 'ext/jquery-ui-1.8.23.custom.min',
    'ext/toastr': 'ext/toastr',
    'ext/underscore': 'ext/underscore-1.3.3',
    'ext/underscore.string': 'ext/underscore.string-2.0.0',
    'ext/validate': 'ext/jquery.validate.min',
    'ext/smartbanner': 'ext/jquery.smartbanner',

    'moment': 'ext/moment',
    'moment-timezone': 'ext/moment-timezone'
  }
});

// Underscore and jQuery need to be loaded first, otherwise RequireJS might try
// to execute things that depend on them first since loading is async
require(['ext/underscore', 'ext/jquery'], function(_, $) {

window._ = _;
window.$ = $;
window.jQuery = $;

// Add a CSRF token to the headers for all ajax requests being sent out by
// jQuery.
$.ajaxSetup({
  headers: {
    'X-CSRF-Token': $('meta[name="csrf-token"]').attr('content')
  }
});

require(['ext/underscore.string', 'util', 'rmc_moment',
    'ext/backbone', 'ext/bootstrap', 'ext/cookie', 'ext/toastr',
    'points', 'user', 'facebook', 'work_queue', 'ext/smartbanner'],
function(_s, util, moment, Backbone, __, __, toastr, _points,
  _user, _facebook, smartbanner) {

 // Show a banner to visitors from Android browsers linking 
 // to our Android app on the Google Play Store.
  $(function() {
    $.smartbanner({
      // Options for the smart banner 
      // https://github.com/jasny/jquery.smartbanner
      title: 'UWFlow',
      author: 'UW Flow',
      // The URL of the icon)
      icon: '../static/img/logo/flow_128x128.png',
      // Set this to 'android' for easy testing on desktop browser
      force: null
    });
  });

  // Add helpers functions to all templates
  (function() {
    var template = _.template;

    // TODO(mack): move templateHelpers into own file
    var templateHelpers = {
      _: _,
      _s: _s,
      pluralize: util.pluralize,
      getDisplayRating: util.getDisplayRating,
      moment: moment,
      capitalize: util.capitalize,
      humanizeTermId: util.humanizeTermId,
      humanizeProfId: util.humanizeProfId,
      normalizeProfName: util.normalizeProfName,
      sectionTypeToCssClass: util.sectionTypeToCssClass,
      splitCourseId: util.splitCourseId,
      termIdToQuestId: util.termIdToQuestId
    };

    _.template = function(templateString, data, settings) {
      templateString = templateString || '';
      if (data) {
        data = _.extend({}, templateHelpers, data);
        return template(templateString, data, settings);
      } else {
        var compiled = template(templateString);
        return function(data, settings) {
          data = _.extend({}, templateHelpers, data);
          return compiled(data, settings);
        };
      }
    };
  })();

  // Set defaults for toastr notifications
  toastr.options = {
    timeOut: 3000
  };

  (function() {
    if ($.fn.tooltip !== undefined && $.fn.popover !== undefined) {
      // Override bootstrap with saner defaults
      var overrides = {
        animation: false
      };
      _.extend($.fn.tooltip.defaults, overrides);
      _.extend($.fn.popover.defaults, overrides);
    }
  })();

  // TODO(mack): separate code inside into functions
  var onDomReady = function() {
    $('.navbar [title]').tooltip({ placement: 'bottom' });
    $('.navbar .signout-btn').click(function() {
      window.location.href = '/?logout=1';
    });

    if (window.pageData.userObjs) {
      _user.UserCollection.addToCache(window.pageData.userObjs);
    }

    var currentUser = _user.getCurrentUser();
    if (currentUser) {
      var userPointsView = new _points.PointsView({ model: currentUser });
      $('#user-points-placeholder').replaceWith(userPointsView.render().$el);
    }

    if (window.pageData.pageScript) {
      require([window.pageData.pageScript]);
    }

    var $footer = $('footer');
    if ($footer.length &&
          !_.contains(['/', '/courses'], window.location.pathname)) {
      // TODO(david): Use jpg and have it fade out into bg color
      $footer.css('background',
        'url(/static/img/footer_uw_sphere_short.png) right top no-repeat');
    }

    $(document.body).on('pageScriptComplete', function(evt) {
      $('[rel="tooltip"]').tooltip();
      $(document.body).data('rendered', true);
    });

    // TODO(Sandy): We don't use these cookies anymore, so remove them from the
    // client. Though this doesn't matter as much anymore, now that we're on
    // HTTPS. This code block can be removed in a few months (Feb. 19, 2014)
    $.removeCookie('fbid', { path: '/' });
    $.removeCookie('fb_access_token', { path: '/' });
    $.removeCookie('fb_access_token_expires_on', { path: '/' });
  };


  // IF the dom ready event has already occurred, binding to jQuery's dom
  // ready listener waits until the loaded event before firing.
  // So manually check if domready has occurred, and if it has execute
  // right away. In IE, gotta wait for state === 'complete' since
  // state === 'interactive' could fire before dom is ready. See
  // https://github.com/UWFlow/rmc/commit/56af16db497db5b8d4e210e784e9f63051fcce32
  // for more info.
  var state = document.readyState;
  if (document.attachEvent ? state === 'complete' : state !== 'loading' ) {
    onDomReady();
  } else {
    $(onDomReady);
  }

});


});

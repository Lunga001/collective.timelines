import json
from zope.component import getMultiAdapter, getAdapters
from Acquisition import aq_inner
from plone import api
from Products.Five.browser import BrowserView
from collective.timelines.interfaces import (ITimelineContent,
                                             ITimelineSupplement)
from collective.timelines.browser.configuration import ITimelineSettings
from Products.CMFCore.utils import getToolByName
from wt.fleet.interfaces import IJob
from zope.component import getUtility
from zope.intid.interfaces import IIntIds


class TimelineView(BrowserView):
    """A view providing timeline settings data"""

    @property
    def start_at_end(self):
        return (ITimelineSettings(self.context).start_at_end and
                'true' or 'false')

    @property
    def font(self):
        return ITimelineSettings(self.context).fonts

    @property
    def map_style(self):
        return ITimelineSettings(self.context).map_style

    @property
    def data_url(self):
        context = self.context
        abs_url = '%s/@@timeline-json' % context.absolute_url()
        return abs_url

    @property
    def resource_base(self):
        return (getToolByName(self.context, 'portal_url')() +
                '/++resource++timelines')

    @property
    def lang(self):
        context = aq_inner(self.context)
        portal_state = getMultiAdapter((context, self.request),
                                       name=u'plone_portal_state')
        return portal_state.language() or 'en'


class TimelineFolderJSON(BrowserView):
    """JSON Representation of folder contents"""

    def __call__(self):
        """test render"""
        self.request.response.setHeader('Content-Type', 'application/json')
        return json.dumps(self.content_data())

    def _get_contents(self):
        context = aq_inner(self.context)
        return context.listFolderContents()

    def content_data(self):
        """Return JSON representation of timeline contents"""
        context = aq_inner(self.context)
        base_data = {"timeline": {"type":"default",
                                  "date": []}}
        data = ITimelineContent(context).data(ignore_date=True)
        base_data['timeline'].update(data)
        contents = self._get_contents()
        dates = base_data['timeline']['date']
        for item in contents:
            item_data = ITimelineContent(item).data()
            if not item_data:
                continue
            updaters = getAdapters((item,), ITimelineSupplement)
            # Sort by name
            for name, updater in sorted(updaters):
                updater.update(item_data)

            dates.append(item_data)

        return base_data


class TimelineTopicJSON(TimelineFolderJSON):
    """JSON representation of topic contents"""

    def _get_contents(self):
        context = aq_inner(self.context)
        # Filter query on content with a timeline date set
        return context.queryCatalog(batch=False, full_objects=True,
                                    sort_on='timeline_date')

class TimelineCollectionJSON(TimelineFolderJSON):
    """JSON representation of topic contents"""

    def content_data(self):
        context = aq_inner(self.context)
        vehicleTitle = context.Title()
        base_data = {"timeline": {"type":"default",
                                  "date": []}}
        #data = ITimelineContent(context).data(ignore_date=True)
        data = {"headline": vehicleTitle,
                "text": "<p>Current KMs/Hours: %s/%s</p>" % (
                                context.getOdometerReading(),
                                context.getHourMeterReading(), 
                                ),
                }
        base_data['timeline'].update(data)
        dates = base_data['timeline']['date']
        intids = getUtility(IIntIds)
        vuuid = intids.getId(context)
        mediaURL = '%s/folder.png' % api.portal.get().absolute_url()
        brains = api.content.find(
                            object_provides=IJob.__identifier__,
                            vehicle=vuuid,
                            sort_on="jobDate")
        # Vehicle - Jobcards
        for brain in brains:
            startDate = brain.wipDate 
            if startDate is None:
                startDate = brain.jobDate
            startDate = "%s,%s,%s" % (
                                        startDate.strftime('%Y'),
                                        startDate.strftime('%m'),
                                        startDate.strftime('%d'),
                                        )
            #TODO: What to do when endDate is None
            endDate = brain.completeDate
            if endDate is None:
                endDate = brain.jobDate
            endDate = "%s,%s,%s" % (
                                        endDate.strftime('%Y'),
                                        endDate.strftime('%m'),
                                        endDate.strftime('%d'),
                                        )
            tag = ''
            if startDate == endDate:
                tag = 'End on same day'
            date_data = {
                            "startDate": startDate,
                            "endDate": endDate,
                            "headline": '%s: %s' % (brain.jobNumber,
                                                    brain.summary),
                            "text":"""<p class='wtf-state-%s'>%s</p>
                                      <p>Go to JobCard: <a href='%s' target='_blank'>
                                        %s</a>
                                      </p>
                                    """ % (
                                            brain.review_state,
                                            brain.review_state,
                                            brain.getURL(),
                                            brain.jobNumber,
                                           ),
                            #"tag": tag,
                            "asset": {
                                "media": mediaURL,
                                "thumbnail":mediaURL,
                                #"credit":"Credit Name Goes Here",
                                #"caption":"Caption text goes here"
                            }
                        }
            dates.append(date_data)

        return base_data

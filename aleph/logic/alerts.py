import logging
from pprint import pprint  # noqa
from banal import ensure_list
from elasticsearch.helpers import scan

from aleph.authz import Authz
from aleph.core import db, es
from aleph.model import Alert, Events
from aleph.index.core import entities_index
from aleph.index.entities import get_entity
from aleph.index.util import unpack_result, authz_query
from aleph.logic.notifications import publish

log = logging.getLogger(__name__)


def check_alerts():
    """Go through all alerts."""
    Alert.dedupe()
    db.session.commit()
    for alert_id in Alert.all_ids():
        check_alert(alert_id)


def check_alert(alert_id):
    alert = Alert.by_id(alert_id)
    if alert is None:
        return
    authz = Authz.from_role(alert.role)
    query = alert_query(alert, authz)
    found = 0
    for result in scan(es, query=query, index=entities_index()):
        entity = unpack_result(result)
        found += 1
        params = {
            'alert': alert,
            'role': alert.role,
            'entity': entity
        }
        publish(Events.MATCH_ALERT,
                actor_id=entity.get('uploader_id'),
                params=params)
        db.session.commit()

    alert.update()
    log.info('Found %d new results for: %s', found, alert.label)
    db.session.commit()
    db.session.close()


def alert_query(alert, authz):
    """Construct a search query to find new matching entities and documents
    for a particular alert. Update handling is done via a timestamp of the
    latest known result."""
    entity = get_entity(alert.entity_id)
    clauses = []
    if entity is None and not alert.query_text:
        # TODO: do we want to delete the alert here?
        clauses.append({'match_none': {}})

    if alert.query_text:
        # Many users have bookmarked complex queries, otherwise we'd use a
        # precise match query.
        clauses.append({
            'simple_query_string': {
                'query': alert.query_text,
                'fields': ['text'],
                'default_operator': 'AND',
                'minimum_should_match': '90%'
            }
        })

    if entity is not None:
        for field in ['names', 'fingerprints', 'emails', 'phones']:
            for value in ensure_list(entity.get(field)):
                clauses.append({'term': {field: value}})
                clauses.append({'match_phrase': {'text': value}})

    return {
        'query': {
            'bool': {
                'should': clauses,
                'filter': [
                    {
                        'range': {
                            'created_at': {'gt': alert.notified_at}
                        }
                    },
                    authz_query(authz)
                ],
                'minimum_should_match': 1
            }
        }
    }

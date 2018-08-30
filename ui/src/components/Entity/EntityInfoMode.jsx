import _ from 'lodash';
import React from 'react';
import { connect } from 'react-redux';
import { FormattedMessage } from 'react-intl';

import { Property, Entity, Schema } from 'src/components/common';
import { CollectionOverview } from 'src/components/Collection';
import { selectSchemata } from 'src/selectors';


class EntityInfoMode extends React.Component {
  render() {
    const { entity, schema } = this.props;
    const isThing = entity && entity.schemata && entity.schemata.indexOf('Thing') !== -1;

    if (schema === undefined) {  // entity hasn't loaded.
      return null;
    }
    
    const entityProperties = _.values(schema.properties).filter((prop) => {
      return !prop.caption && (schema.featured.indexOf(prop.name) !== -1 || entity.properties[prop.name]);
    });
    
    return (
      <React.Fragment>
        <div className="pane-heading">
          <span>
            <Schema.Label schema={entity.schema} icon={true} />
          </span>
          <h1>
            {isThing && (
              <Entity.Label entity={entity} addClass={true}/>
            )}
          </h1>
        </div>
        <div className="pane-content">
          <ul className="info-sheet">
            { entityProperties.map((prop) => (
              <li key={prop.name}>
                <span className="key">
                  <Property.Name model={prop} />
                </span>
                <span className="value">
                  <Property.Values model={prop} values={entity.properties[prop.name]} />
                </span>
              </li>
            ))}
          </ul>
          <span className="source-header">
            <FormattedMessage id="entity.info.source" defaultMessage="Source"/>
          </span>
          <CollectionOverview collection={entity.collection} hasHeader={true}/>   
        </div>
      </React.Fragment>
    );
  }
}

const mapStateToProps = (state, ownProps) => {
  const { entity } = ownProps;
  return {
    schema: selectSchemata(state)[entity.schema]
  };
};

EntityInfoMode = connect(mapStateToProps, {})(EntityInfoMode);
export default EntityInfoMode;
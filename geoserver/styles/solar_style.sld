<?xml version="1.0" encoding="UTF-8"?>
<StyledLayerDescriptor version="1.0.0"
  xmlns="http://www.opengis.net/sld"
  xmlns:ogc="http://www.opengis.net/ogc"
  xmlns:xlink="http://www.w3.org/1999/xlink"
  xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
  xsi:schemaLocation="http://www.opengis.net/sld http://schemas.opengis.net/sld/1.0.0/StyledLayerDescriptor.xsd">
  <NamedLayer>
    <Name>solar_style</Name>
    <UserStyle>
      <Title>Solar Suitability</Title>
      <FeatureTypeStyle>
        <Rule>
          <Title>High solar suitability</Title>
          <ogc:Filter>
            <ogc:PropertyIsGreaterThanOrEqualTo>
              <ogc:PropertyName>suitability_score</ogc:PropertyName>
              <ogc:Literal>85</ogc:Literal>
            </ogc:PropertyIsGreaterThanOrEqualTo>
          </ogc:Filter>
          <PolygonSymbolizer>
            <Fill>
              <CssParameter name="fill">#d58b18</CssParameter>
              <CssParameter name="fill-opacity">0.74</CssParameter>
            </Fill>
            <Stroke>
              <CssParameter name="stroke">#9b5f0c</CssParameter>
              <CssParameter name="stroke-width">1.5</CssParameter>
            </Stroke>
          </PolygonSymbolizer>
        </Rule>
        <Rule>
          <Title>Medium solar suitability</Title>
          <ogc:Filter>
            <ogc:PropertyIsBetween>
              <ogc:PropertyName>suitability_score</ogc:PropertyName>
              <ogc:LowerBoundary><ogc:Literal>70</ogc:Literal></ogc:LowerBoundary>
              <ogc:UpperBoundary><ogc:Literal>84</ogc:Literal></ogc:UpperBoundary>
            </ogc:PropertyIsBetween>
          </ogc:Filter>
          <PolygonSymbolizer>
            <Fill>
              <CssParameter name="fill">#efc15c</CssParameter>
              <CssParameter name="fill-opacity">0.64</CssParameter>
            </Fill>
            <Stroke>
              <CssParameter name="stroke">#9b5f0c</CssParameter>
              <CssParameter name="stroke-width">1.2</CssParameter>
            </Stroke>
          </PolygonSymbolizer>
        </Rule>
        <Rule>
          <Title>Low solar suitability</Title>
          <ElseFilter/>
          <PolygonSymbolizer>
            <Fill>
              <CssParameter name="fill">#f2dfaa</CssParameter>
              <CssParameter name="fill-opacity">0.40</CssParameter>
            </Fill>
            <Stroke>
              <CssParameter name="stroke">#bd842c</CssParameter>
              <CssParameter name="stroke-width">0.8</CssParameter>
            </Stroke>
          </PolygonSymbolizer>
        </Rule>
      </FeatureTypeStyle>
    </UserStyle>
  </NamedLayer>
</StyledLayerDescriptor>

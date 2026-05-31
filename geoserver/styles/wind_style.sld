<?xml version="1.0" encoding="UTF-8"?>
<StyledLayerDescriptor version="1.0.0"
  xmlns="http://www.opengis.net/sld"
  xmlns:ogc="http://www.opengis.net/ogc"
  xmlns:xlink="http://www.w3.org/1999/xlink"
  xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
  xsi:schemaLocation="http://www.opengis.net/sld http://schemas.opengis.net/sld/1.0.0/StyledLayerDescriptor.xsd">
  <NamedLayer>
    <Name>wind_style</Name>
    <UserStyle>
      <Title>Wind Suitability</Title>
      <FeatureTypeStyle>
        <Rule>
          <Title>High wind suitability</Title>
          <ogc:Filter>
            <ogc:PropertyIsGreaterThanOrEqualTo>
              <ogc:PropertyName>suitability_score</ogc:PropertyName>
              <ogc:Literal>85</ogc:Literal>
            </ogc:PropertyIsGreaterThanOrEqualTo>
          </ogc:Filter>
          <PolygonSymbolizer>
            <Fill>
              <CssParameter name="fill">#5a6fb0</CssParameter>
              <CssParameter name="fill-opacity">0.72</CssParameter>
            </Fill>
            <Stroke>
              <CssParameter name="stroke">#384d91</CssParameter>
              <CssParameter name="stroke-width">1.5</CssParameter>
            </Stroke>
          </PolygonSymbolizer>
        </Rule>
        <Rule>
          <Title>Medium wind suitability</Title>
          <ogc:Filter>
            <ogc:PropertyIsBetween>
              <ogc:PropertyName>suitability_score</ogc:PropertyName>
              <ogc:LowerBoundary><ogc:Literal>70</ogc:Literal></ogc:LowerBoundary>
              <ogc:UpperBoundary><ogc:Literal>84</ogc:Literal></ogc:UpperBoundary>
            </ogc:PropertyIsBetween>
          </ogc:Filter>
          <PolygonSymbolizer>
            <Fill>
              <CssParameter name="fill">#8ca0d3</CssParameter>
              <CssParameter name="fill-opacity">0.62</CssParameter>
            </Fill>
            <Stroke>
              <CssParameter name="stroke">#384d91</CssParameter>
              <CssParameter name="stroke-width">1.2</CssParameter>
            </Stroke>
          </PolygonSymbolizer>
        </Rule>
        <Rule>
          <Title>Low wind suitability</Title>
          <ElseFilter/>
          <PolygonSymbolizer>
            <Fill>
              <CssParameter name="fill">#c9d1ea</CssParameter>
              <CssParameter name="fill-opacity">0.36</CssParameter>
            </Fill>
            <Stroke>
              <CssParameter name="stroke">#6f7fb5</CssParameter>
              <CssParameter name="stroke-width">0.8</CssParameter>
            </Stroke>
          </PolygonSymbolizer>
        </Rule>
      </FeatureTypeStyle>
    </UserStyle>
  </NamedLayer>
</StyledLayerDescriptor>

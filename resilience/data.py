"""Data loading: TNTP network + geojson, link geometry join, CRS handling."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import yaml
import pandas as pd
import geopandas as gpd
from shapely.geometry import LineString, Point
import network as net_module


def load_config(config_path: str) -> dict:
    with open(config_path) as f:
        return yaml.safe_load(f)


def load_network(config: dict):
    """Load a Network from config paths. Returns the Network object."""
    return net_module.Network(config['network'], config['trips'])


def build_link_geodataframe(net, config: dict) -> gpd.GeoDataFrame:
    """Return a GeoDataFrame of all links, with geometry if geojson available.

    Columns: link_id, tail, head, capacity, length, fft, alpha, beta,
             flow, cost, vc, closed, geometry (LineString or None).
    """
    records = []
    for lid, lk in net.link.items():
        records.append({
            'link_id': lid,
            'tail': lk.tail,
            'head': lk.head,
            'capacity': lk.capacity,
            'length': lk.length,
            'fft': lk.freeFlowTime,
            'alpha': lk.alpha,
            'beta': lk.beta,
            'flow': lk.flow,
            'cost': lk.cost,
            'vc': lk.flow / lk.capacity if lk.capacity > 0 else 0.0,
            'closed': False,
        })
    df = pd.DataFrame(records)

    geojson_path = config.get('geojson_links')
    if geojson_path and os.path.exists(geojson_path):
        gdf_geo = gpd.read_file(geojson_path)
        # Build join key matching network.py's link ID format
        gdf_geo['link_id'] = (
            '(' + gdf_geo['init_node'].astype(str) + ',' + gdf_geo['term_node'].astype(str) + ')'
        )
        geo_lookup = gdf_geo.set_index('link_id')['geometry'].to_dict()
        df['geometry'] = df['link_id'].map(geo_lookup)
        gdf = gpd.GeoDataFrame(df, geometry='geometry', crs='EPSG:4326')
    else:
        df['geometry'] = None
        gdf = gpd.GeoDataFrame(df, geometry='geometry')

    return gdf


def build_node_geodataframe(config: dict) -> gpd.GeoDataFrame:
    """Return a GeoDataFrame of network nodes if geojson available, else empty."""
    geojson_path = config.get('geojson_nodes')
    if geojson_path and os.path.exists(geojson_path):
        return gpd.read_file(geojson_path).rename(columns={'id': 'node_id'})
    return gpd.GeoDataFrame(columns=['node_id', 'geometry'])


def reproject_links(gdf: gpd.GeoDataFrame, target_crs: str) -> gpd.GeoDataFrame:
    """Reproject a link GeoDataFrame to a metric CRS."""
    if gdf.crs is None:
        return gdf
    return gdf.to_crs(target_crs)

from flask import Flask, jsonify, request
from flask_cors import CORS
import psycopg2
import json

app = Flask(__name__)
CORS(app)

conn = psycopg2.connect(
    host='aws-0-ap-southeast-1.pooler.supabase.com',  # Host dari Supabase pooler
    database='postgres',                               # Nama database
    user='postgres.wtmfsznnmyinbgzkdofz',             # Nama penggunag
    password='palaparingproject',                   # Ganti dengan password yang benar
    port='5432',                                       # Port untuk pooler
    options='-c pool_mode=session'                     # Menentukan mode pool
)


FIELD_ORDER = {
    "Palapa_Ring_Barat_Alur": [
        "Link", "Project", "Panjang Kabel Laut", "Panjang Kabel Darat", "Total Panjang Kabel",
        "Kapasitas Palapa Ring", "Telkom Sewa", "Okupansi Telkom (%)", "Media Transmisi", "Updated at"
    ],
    "Palapa_Ring_Tengah_Alur": [
        "Link", "Project", "Panjang Kabel Laut", "Panjang Kabel Darat", "Total Panjang Kabel",
        "Kapasitas Palapa Ring", "Telkom Sewa", "Okupansi Telkom (%)", "Media Transmisi", "Updated at"
    ],
    "Palapa_Ring_Timur_Alur": [
        "Link", "Project", "Panjang Kabel Laut", "Panjang Kabel Darat", "Total Panjang Kabel",
        "Kapasitas Palapa Ring", "Telkom Sewa", "Okupansi Telkom (%)", "Media Transmisi", "Updated at"
    ],
    "Palapa_Ring_Barat_Point": [
        "fid", "Nama", "Project", "Nama Kota", "Nama Provinsi",
        "Longitude", "Latitude", "Keterangan", "Media Transmisi", "Updated at"
    ],
    "Palapa_Ring_Tengah_Point": [
        "fid", "Nama", "Project", "Nama Kota", "Nama Provinsi",
        "Longitude", "Latitude", "Keterangan", "Media Transmisi", "Updated at"
    ],
    "Palapa_Ring_Timur_Point": [
        "fid", "Nama", "Project", "Nama Kota", "Nama Provinsi",
        "Longitude", "Latitude", "Keterangan", "Media Transmisi", "Updated at"
    ],
    "SubmarineCable_Alur": [
        "fid", "Link", "Description"
    ]
}

def get_geojson_from_table(table_name):
    cur = conn.cursor()
    cur.execute(f'SELECT *, ST_AsGeoJSON(geom) FROM "{table_name}"')
    rows = cur.fetchall()
    colnames = [desc[0] for desc in cur.description]

    ordered_keys = FIELD_ORDER.get(table_name, colnames[:-1])

    features = []
    for row in rows:
        full_props = dict(zip(colnames, row))
        props = {key: full_props.get(key, "") for key in ordered_keys}
        feature = {
            "type": "Feature",
            "geometry": json.loads(row[-1]),
            "properties": props
        }
        features.append(feature)

    geojson = {
        "type": "FeatureCollection",
        "features": features,
        "field_order": ordered_keys
    }
    return geojson

# Endpoint GET data
@app.route('/api/point/barat')
def point_barat():
    return jsonify(get_geojson_from_table("Palapa_Ring_Barat_Point"))

@app.route('/api/alur/barat')
def alur_barat():
    return jsonify(get_geojson_from_table("Palapa_Ring_Barat_Alur"))

@app.route('/api/point/tengah')
def point_tengah():
    return jsonify(get_geojson_from_table("Palapa_Ring_Tengah_Point"))

@app.route('/api/alur/tengah')
def alur_tengah():
    return jsonify(get_geojson_from_table("Palapa_Ring_Tengah_Alur"))

@app.route('/api/point/timur')
def point_timur():
    return jsonify(get_geojson_from_table("Palapa_Ring_Timur_Point"))

@app.route('/api/alur/timur')
def alur_timur():
    return jsonify(get_geojson_from_table("Palapa_Ring_Timur_Alur"))

@app.route('/api/alur/submarine')
def alus_submarine():
    return jsonify(get_geojson_from_table("SubmarineCable_Alur"))

# ✨ Endpoint dinamis update data dan Updated at
@app.route('/api/update/<table_name>/<int:fid>', methods=['POST'])
def update_table(table_name, fid):
    data = request.get_json()
    if not data:
        return jsonify({"error": "No data provided"}), 400

    # Siapkan list kolom yang akan diupdate, dan value-nya
    set_clauses = []
    values = []
    for key, value in data.items():
        set_clauses.append(f'"{key}" = %s')
        values.append(value)

    # Tambahkan kolom Updated at = NOW()
    set_clauses.append('"Updated at" = NOW()')

    # Query update
    sql = f'UPDATE "{table_name}" SET {", ".join(set_clauses)} WHERE fid = %s'
    values.append(fid)

    try:
        cur = conn.cursor()
        cur.execute(sql, values)
        conn.commit()
        cur.close()
        return jsonify({"message": f"Table {table_name} fid {fid} updated successfully"})
    except Exception as e:
        conn.rollback()
        return jsonify({"error": str(e)}), 500

# Run server
if __name__ == '__main__':
    app.run(debug=True)

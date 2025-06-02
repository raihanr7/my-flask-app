from flask import Flask, jsonify, request, render_template
from flask_cors import CORS
import psycopg2
import json
import pytz
from datetime import datetime

app = Flask(__name__)
CORS(app)

# Koneksi ke database PostgreSQL menggunakan Supabase pooler
conn = psycopg2.connect(
    host='aws-0-ap-southeast-1.pooler.supabase.com',  # Supabase pooler host
    database='postgres',                               # Nama database
    user='postgres.wtmfsznnmyinbgzkdofz',              # Username Supabase
    password='palaparingproject',                      # Password Supabase
    port='6543',                                       # Port pooler
    options='-c timezone=UTC -c pool_mode=transaction' # Jalankan di UTC, lalu convert di kode
)

# Urutan field untuk properti GeoJSON
FIELD_ORDER = {
    "Palapa_Ring_Barat_Alur": [
        "Link", "Project", "Panjang Kabel Laut", "Panjang Kabel Darat",
        "Total Panjang Kabel", "Kapasitas Palapa Ring",
        "Telkom Sewa", "Okupansi Telkom (%)", "Media Transmisi", "Updated at"
    ],
    "Palapa_Ring_Barat_Point": [
        "fid", "Nama", "Project", "Nama Kota", "Nama Provinsi",
        "Longitude", "Latitude", "Keterangan", "Media Transmisi", "Updated at"
    ],
    "Palapa_Ring_Tengah_Alur": [
        "Link", "Project", "Panjang Kabel Laut", "Panjang Kabel Darat",
        "Total Panjang Kabel", "Kapasitas Palapa Ring",
        "Telkom Sewa", "Okupansi Telkom (%)", "Media Transmisi", "Updated at"
    ],
    "Palapa_Ring_Tengah_Point": [
        "fid", "Nama", "Project", "Nama Kota", "Nama Provinsi",
        "Longitude", "Latitude", "Keterangan", "Media Transmisi", "Updated at"
    ],
    "Palapa_Ring_Timur_Alur": [
        "Link", "Project", "Panjang Kabel Laut", "Panjang Kabel Darat",
        "Total Panjang Kabel", "Kapasitas Palapa Ring",
        "Telkom Sewa", "Okupansi Telkom (%)", "Media Transmisi", "Updated at"
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

    # Siapkan zona waktu WIB
    wib_tz = pytz.timezone('Asia/Jakarta')

    ordered_keys = FIELD_ORDER.get(table_name, colnames[:-1])
    features = []

    for row in rows:
        full_props = dict(zip(colnames, row))

        # Konversi kolom "Updated at" ke WIB
        if "Updated at" in full_props and full_props["Updated at"]:
            utc_dt = full_props["Updated at"]  # objek datetime aware (UTC)
            wib_dt = utc_dt.astimezone(wib_tz)
            full_props["Updated at"] = wib_dt.strftime('%Y-%m-%d %H:%M:%S')

        # Ambil properti sesuai urutan
        props = {key: full_props.get(key, "") for key in ordered_keys}

        feature = {
            "type": "Feature",
            "geometry": json.loads(row[-1]),    # GeoJSON geometry
            "properties": props
        }
        features.append(feature)

    return {
        "type": "FeatureCollection",
        "features": features,
        "field_order": ordered_keys
    }

# Rute homepage
@app.route('/')
def index():
    return render_template('Peta Palapa Ring Semi-Realtime.html')

# Endpoint GET untuk data poin dan alur
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

# Endpoint dinamis untuk update data (otomatis set Updated at)
@app.route('/api/update/<table_name>/<int:fid>', methods=['POST'])
def update_table(table_name, fid):
    data = request.get_json()
    if not data:
        return jsonify({"error": "No data provided"}), 400

    # Siapkan klausa SET, otomatis menambahkan Updated at = NOW()
    set_clauses = []
    values = []
    for key, value in data.items():
        set_clauses.append(f'"{key}" = %s')
        values.append(value)
    set_clauses.append('"Updated at" = NOW()')

    sql = f'UPDATE "{table_name}" SET {", ".join(set_clauses)} WHERE fid = %s'
    values.append(fid)

    try:
        cur = conn.cursor()
        cur.execute(sql, values)
        conn.commit()
        cur.close()
        return jsonify({"message": f"Updated {table_name} fid {fid}"})
    except Exception as e:
        conn.rollback()
        return jsonify({"error": str(e)}), 500

# Jalankan server
if __name__ == '__main__':
    app.run(debug=True)

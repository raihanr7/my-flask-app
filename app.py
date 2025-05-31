from flask import Flask, jsonify, request, render_template
from flask_cors import CORS
import psycopg2
import json

app = Flask(__name__)
CORS(app)

# Koneksi ke database PostgreSQL menggunakan Supabase pooler
conn = psycopg2.connect(
    host='https://wtmfsznnmyinbgzkdofz.supabase.co',  # Host dari Supabase pooler
    database='postgres',                               # Nama database
    user='postgres.wtmfsznnmyinbgzkdofz',             # Nama pengguna
    password='palaparingproject',                      # Ganti dengan password yang benar
    port='6543',                                       # Port untuk pooler
    options='-c pool_mode=session'                     # Menentukan mode pool
)

FIELD_ORDER = {
    "Palapa_Ring_Barat_Alur": [
        "Link", "Project", "Panjang Kabel Laut", "Panjang Kabel Darat", "Total Panjang Kabel",
        "Kapasitas Palapa Ring", "Telkom Sewa", "Okupansi Telkom (%)", "Media Transmisi", "Updated at"
    ],
    "Palapa_Ring_Barat_Point": [
        "fid", "Nama", "Project", "Nama Kota", "Nama Provinsi",
        "Longitude", "Latitude", "Keterangan", "Media Transmisi", "Updated at"
    ],
    # Tambahkan entri untuk tabel lainnya
}

def get_geojson_from_table(table_name):
    cur = conn.cursor()
    cur.execute(f'SELECT *, ST_AsGeoJSON(geom) FROM "{table_name}"')  # Pastikan 'geom' ada di tabel
    rows = cur.fetchall()
    colnames = [desc[0] for desc in cur.description]

    ordered_keys = FIELD_ORDER.get(table_name, colnames[:-1])

    features = []
    for row in rows:
        full_props = dict(zip(colnames, row))
        props = {key: full_props.get(key, "") for key in ordered_keys}
        feature = {
            "type": "Feature",
            "geometry": json.loads(row[-1]),  # Mengambil geometri dari hasil SQL
            "properties": props
        }
        features.append(feature)

    geojson = {
        "type": "FeatureCollection",
        "features": features,
        "field_order": ordered_keys
    }
    return geojson

# Rute untuk halaman utama (homepage)
@app.route('/')
def index():
    return render_template('Peta Palapa Ring Semi-Realtime.html')  # Menyajikan file HTML

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

# ✨ Endpoint dinamis untuk update data dan "Updated at"
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

# Menjalankan server
if __name__ == '__main__':
    app.run(debug=True)

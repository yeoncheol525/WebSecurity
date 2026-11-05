from urllib.parse import urlencode

from flask import abort, jsonify, redirect, request

from common.runtime import create_base_app, query


PRODUCT_FIELDS = "item_key AS id, label AS name, description, amount AS price"


def serialize(row):
    return {**row, "price": format(row["price"], ".2f")}


def create_app():
    app = create_base_app("catalog")

    @app.get("/products")
    def products():
        if request.accept_mimetypes.best_match(["application/json", "text/html"]) == "text/html":
            term = request.args.get("q", request.args.get("keyword", ""))
            return redirect("/shop?" + urlencode({"q": term}))
        term = request.args.get("q", "")
        if len(term) > 100:
            abort(400)
        # LIKE wildcards are data too; ordinary searches use literal matching.
        term = term.replace("!", "!!").replace("%", "!%").replace("_", "!_")
        rows = query(
            "catalog.search",
            "SELECT " + PRODUCT_FIELDS + " FROM catalog.public_products "
            "WHERE label ILIKE %s ESCAPE '!' ORDER BY item_key LIMIT 100",
            (f"%{term}%",), fetch="all",
        )
        return jsonify(products=[serialize(row) for row in rows])

    @app.get("/products/<int:product_id>")
    def product(product_id):
        row = query("catalog.detail", "SELECT " + PRODUCT_FIELDS +
                    " FROM catalog.public_products WHERE item_key = %s",
                    (product_id,), fetch="one")
        if row is None:
            abort(404)
        return jsonify(product=serialize(row))

    return app

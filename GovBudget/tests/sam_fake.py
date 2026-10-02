"""A fake SAM Entity Management API for the SAM tests: an httpx handler that
answers the documented query shapes from a registry of UEI -> kind.

Shapes, from https://open.gsa.gov/api/entity-api/ (read 2026-09-27): a
registration (samRegistered "Yes"); an ID-only entity (samRegistered "No",
whose registrationStatus may still read "Active" — docs Example 2); the
masked record of an entity that opted out of public display, returned only
when integrityInformation is requested (Example 6); up to 10 records a page,
with totalRecords counting every match.
"""
from __future__ import annotations

import urllib.parse

import httpx

MASK = ("This entity has opted out of public search. Only federal government "
        "users and users associated with this entity can view this record on "
        "SAM.gov.")


def registration(uei, status="Active", expires="2027-01-01", name=None):
    return {
        "entityRegistration": {
            "ueiSAM": uei, "legalBusinessName": name if name is not None
            else f"CO {uei}", "cageCode": "1ABC2", "samRegistered": "Yes",
            "registrationStatus": status, "registrationExpirationDate": expires},
        "coreData": {"businessTypes": {"businessTypeList": [
            {"businessTypeDesc": "Corporate Entity, Not Tax Exempt"}]}},
        "assertions": {"goodsAndServices": {"primaryNaics": "336411"}},
    }


def id_only(uei):
    return {"entityRegistration": {"ueiSAM": uei, "legalBusinessName": f"ID {uei}",
                                   "samRegistered": "No",
                                   "registrationStatus": "Active"},
            "coreData": {"physicalAddress": {"countryCode": "USA"}}}


def masked(uei):
    return {"entityRegistration": MASK, "coreData": MASK, "assertions": MASK,
            "integrityInformation": {"entitySummary": {
                "ueiSAM": uei, "legalBusinessName": f"HIDDEN {uei}"}}}


class FakeSam:
    """kinds: registered (default), inactive (an expired registration),
    id_only, opted_out, none, dup (two Active registrations), noname."""

    def __init__(self, kinds=None, *, honour_batches=True,
                 honour_integrity=True, default_hides_expired=False,
                 fail=None):
        self.kinds = dict(kinds or {})
        self.honour_batches = honour_batches
        self.honour_integrity = honour_integrity
        self.default_hides_expired = default_hides_expired
        self.fail = fail
        self.requests: list[dict] = []

    def __call__(self, request: httpx.Request) -> httpx.Response:
        raw = bytes(request.url.raw_path).decode()
        query = raw.split("?", 1)[1] if "?" in raw else ""
        q = dict(part.split("=", 1) for part in query.split("&") if "=" in part)
        q = {k: urllib.parse.unquote(v) for k, v in q.items()}
        self.requests.append(q)
        if self.fail is not None:
            out = self.fail(len(self.requests) - 1, q)
            if isinstance(out, Exception):
                raise out
            if out is not None:
                return out
        integrity = "integrityInformation" in q.get("includeSections", "")
        if integrity and not self.honour_integrity:
            return httpx.Response(400, json={"message": "Invalid Input",
                                             "detail": "includeSections"})
        value = q.get("ueiSAM", "")
        if value.startswith("[") and value.endswith("]"):
            ueis = value[1:-1].split("~") if self.honour_batches else [value]
        else:
            ueis = [value]
        stage = ("id_assigned" if q.get("samRegistered") == "No" else
                 "expired" if q.get("registrationStatus") == "E" else
                 "registered")
        records = []
        for u in ueis:
            # An unhonoured batch asks for the literal "[A~B]": no such UEI.
            kind = "none" if u.startswith("[") else self.kinds.get(u, "registered")
            if stage == "registered":
                if kind == "registered":
                    records.append(registration(u))
                elif kind == "dup":
                    records += [registration(u, expires="2026-01-01"),
                                registration(u, expires="2027-06-30")]
                elif kind == "noname":
                    records.append(registration(u, name=""))
                elif kind == "inactive" and not self.default_hides_expired:
                    records.append(registration(u, "Inactive", "2020-02-01"))
                elif kind == "opted_out" and integrity:
                    records.append(masked(u))
            elif stage == "id_assigned" and kind == "id_only":
                records.append(id_only(u))
            elif stage == "expired" and kind == "inactive":
                records.append(registration(u, "Inactive", "2020-02-01"))
        return httpx.Response(200, json={"totalRecords": len(records),
                                         "entityData": records[:10]})

    def asked(self, n: int) -> list[str]:
        value = self.requests[n].get("ueiSAM", "")
        return value[1:-1].split("~") if value.startswith("[") else [value]

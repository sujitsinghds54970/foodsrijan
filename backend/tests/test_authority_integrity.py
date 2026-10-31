from app.services.authority_integrity import check_canonical_super_ceo_integrity


class Query:
    def __init__(self, count):
        self.count_value = count

    def filter(self, *args, **kwargs):
        return self

    def count(self):
        return self.count_value


class DB:
    def __init__(self, count):
        self.count_value = count

    def query(self, _model):
        return Query(self.count_value)


def test_integrity_accepts_exactly_one_active_canonical_super_ceo():
    assert check_canonical_super_ceo_integrity(DB(1)) is True


def test_integrity_rejects_zero_active_canonical_super_ceos():
    assert check_canonical_super_ceo_integrity(DB(0)) is False


def test_integrity_rejects_multiple_active_canonical_super_ceos():
    assert check_canonical_super_ceo_integrity(DB(2)) is False

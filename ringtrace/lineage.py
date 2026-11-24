from .errors import DomainError


class BandIndex:
    """Index each connected chain and the half-open lifetime of each band."""

    def __init__(self, links):
        self.incoming = {link['new_band']: link for link in links}
        self.outgoing = {link['old_band']: link for link in links}
        self.proofs = {link['proof'] for link in links}
        self.roots = {}
        for band in self.outgoing.keys() - self.incoming.keys():
            self.roots[band] = band
            current = band
            while current in self.outgoing:
                current = self.outgoing[current]['new_band']
                self.roots[current] = band

    def verify_link(self, row):
        old, new, moment = row['old_band'], row['new_band'], row['effective_at']
        if row['proof'] in self.proofs or old in self.outgoing or new in self.incoming:
            raise DomainError('link_overlap', '凭据编号或环号交接方向已被占用。', 409)
        if self.roots.get(old, old) == self.roots.get(new, new):
            raise DomainError('link_cycle', '该凭据会把环号接回自己的谱系。', 409)
        earlier, later = self.incoming.get(old), self.outgoing.get(new)
        if (earlier and earlier['effective_at'] >= moment) or (later and moment >= later['effective_at']):
            raise DomainError('link_order', '交接时刻须严格位于前后换环时刻之间。', 409)

    def locate(self, band, moment):
        before, after = self.incoming.get(band), self.outgoing.get(band)
        valid = not ((before and moment < before['effective_at']) or (after and moment >= after['effective_at']))
        proofs = [link['proof'] for link in (before, after) if link]
        return self.roots.get(band, band), valid, proofs

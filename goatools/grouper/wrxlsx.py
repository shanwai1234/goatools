"""Given user GO ids and parent terms, group user GO ids under one parent term.

   Given a group of GO ids with one or more higher-level grouping terms, group
   each user GO id under the most descriptive parent GO term.

   Each GO id may have more than one parent.  One of the parent(s) is chosen
   to best represent the user GO id's function. The choice of parent is made by
   regarding how close the parent GO id is to the bottom of its hierarchy.

   The estimation of how close a GO term is to "the bottom" of its GO hierarchy
   is estimated using the number of total Go term descendent counts below
   that term.
"""
from __future__ import print_function

# import sys
from goatools.go_enrichment import GOEnrichmentStudy
from goatools.wr_tbl import prt_txt
from goatools.wr_tbl import wr_xlsx
from goatools.wr_tbl import wr_xlsx_sections

from goatools.gosubdag.rpt.wr_xlsx import GoSubDagWr
from goatools.grouper.utils import get_hdridx_flds
from goatools.grouper.tasks import SummarySec2dHdrGos

__copyright__ = "Copyright (C) 2016-2018, DV Klopfenstein, H Tang, All rights reserved."
__author__ = "DV Klopfenstein"


class WrXlsxSortedGos(object):
    """Writes grouped and sorted user GO IDs into an xlsx file."""

    kw_keys_xlsx = set(["title", "hdrs"])

    def __init__(self, sortname, sortobj, ver_list=None):
        self.ver_list = ver_list
        self.sortname = sortname
        self.sortobj = sortobj

    def wr_xlsx_gos(self, fout_xlsx, **kws_usr):
        """Write an Excel spreadsheet with user GO ids, grouped under broader GO terms."""
        # Keyword arguments: control content
        desc2nts = self.sortobj.get_desc2nts(**kws_usr)
        # Keyword arguments: control xlsx format
        self.wr_xlsx_nts(fout_xlsx, desc2nts, **kws_usr)
        return desc2nts

    def wr_xlsx_nts(self, fout_xlsx, desc2nts, **kws_usr):
        """Print grouped and sorted GO IDs."""
        kws_xlsx = self._get_xlsx_kws(**kws_usr)
        self._adjust_prt_flds(kws_xlsx, desc2nts, **kws_usr)
        # 1-D: data to print is a flat list of namedtuples
        if 'flat' in desc2nts:
            nts = desc2nts.get('flat')
            # sys.stdout.write("FLAT NTS: {FLDS}\n".format(FLDS=" ".join(next(iter(nts))._fields)))
            wr_xlsx(fout_xlsx, nts, **kws_xlsx)
        # 2-D: data to print is a list of [(section, nts), ...
        else:
            sections_hdrgos = desc2nts.get('sections')
            wr_xlsx_sections(fout_xlsx, sections_hdrgos, **kws_xlsx)

    def wr_txt_gos(self, fout_txt, **kws_usr):
        """Write an Excel spreadsheet with user GO ids, grouped under broader GO terms."""
        # Keyword arguments: control content: hdrgo_prt section_prt top_n use_sections
        desc2nts = self.sortobj.get_desc2nts(**kws_usr)
        # Keyword arguments: control txt format
        self.wr_txt_nts(fout_txt, desc2nts)
        return desc2nts

    def wr_txt_nts(self, fout_txt, desc2nts, prtfmt=None):
        """Write grouped and sorted GO IDs to GOs."""
        with open(fout_txt, 'wb') as prt:
            summary_dct = self.prt_txt_desc2nts(prt, desc2nts, prtfmt)
            if summary_dct:
                print(self.sortobj.grprobj.fmtsum.format(
                    ACTION="WROTE:", FILE=fout_txt, **summary_dct))
            else:
                print("  WROTE: {TXT}".format(TXT=fout_txt))

    def prt_txt_desc2nts(self, prt, desc2nts, prtfmt=None):
        """Print grouped and sorted GO IDs."""
        if prtfmt is None:
            prtfmt = self._get_prtfmt("fmta")
        if self.ver_list is not None:
            prt.write("# Versions:\n#    {VER}\n".format(VER="\n#    ".join(self.ver_list)))
        # 1-D: data to print is a flat list of namedtuples
        if 'flat' in desc2nts:
            nts = desc2nts.get('flat')
            # sys.stdout.write("FLAT NTS: {FLDS}\n".format(FLDS=" ".join(next(iter(nts))._fields)))
            prt_txt(prt, nts, prtfmt)
        # 2-D: data to print is a list of [(section, nts), ...
        else:
            for section, nts in desc2nts['sections']:
                prt.write("\nSECTION: {SEC}\n".format(SEC=section))
                prt_txt(prt, nts, prtfmt)
            grprobj = self.sortobj.grprobj
            dat = SummarySec2dHdrGos().summarize_sec2hdrnts(desc2nts['sections'])
            ugos_y = dat['G'].intersection(grprobj.usrgos)
            ugos_n = dat['U'].intersection(grprobj.usrgos)
            return {'GO_DESC':'usr', 'SECs':len(dat['S']), 'GOs':len(ugos_y),
                    'UNGRP':len(ugos_n), 'undesc':'ungrpd'}

    # -- internal methods ---------------------------------------------------------
    def _get_xlsx_kws(self, **kws_usr):
        """Return keyword arguments relevant to writing an xlsx."""
        kws_xlsx = {'fld2col_widths':self._get_fld2col_widths(**kws_usr), 'items':'GO IDs'}
        remaining_keys = set(["title", "hdrs", "prt_flds"])
        for usr_key, usr_val in kws_usr.items():
            if usr_key in remaining_keys:
                kws_xlsx[usr_key] = usr_val
        return kws_xlsx

    def _adjust_prt_flds(self, kws_xlsx, desc2nts, **kws_usr):
        """Print user-requested fields or provided fields minus info fields."""
        # Use xlsx prt_flds from the user, if provided
        if "prt_flds" in kws_xlsx:
            return kws_xlsx["prt_flds"]
        # If the user did not provide specific fields to print in an xlsx file:
        dont_print = set(['hdr_idx', 'is_hdrgo', 'is_usrgo'])
        # Are we printing GO group headers?
        top_n = None if 'sections' not in desc2nts else kws_usr.get('top_n', None)
        hdrgo_prt = False if top_n is not None else kws_usr.get("hdrgo_prt", True)
        # Build new list of xlsx print fields, excluding those which add no new information
        prt_flds_adjusted = []
        nt_flds = self.sortobj.get_fields(desc2nts)
        for nt_fld in nt_flds:
            if nt_fld not in dont_print:
                # Only add grey-shade to hdrgo and section name rows if hdrgo_prt=True
                if nt_fld == "format_txt":
                    if hdrgo_prt is True:
                        prt_flds_adjusted.append(nt_fld)
                else:
                    prt_flds_adjusted.append(nt_fld)
        kws_xlsx['prt_flds'] = prt_flds_adjusted

    def _get_fld2col_widths(self, **kws):
        """Return xlsx column widths based on default and user-specified field-value pairs."""
        fld2col_widths = self._init_fld2col_widths()
        if 'fld2col_widths' not in kws:
            return fld2col_widths
        for fld, val in kws['fld2col_widths'].items():
            fld2col_widths[fld] = val
        return fld2col_widths

    @staticmethod
    def _init_fld2col_widths():
        """Return default column widths for writing an Excel Spreadsheet."""
        # GO info namedtuple fields: NS dcnt level depth GO D1 name
        # GO header namedtuple fields: format_txt hdr_idx
        fld2col_widths = GoSubDagWr.fld2col_widths.copy()
        for fld, wid in GOEnrichmentStudy.default_fld2col_widths.items():
            fld2col_widths[fld] = wid
        for fld in get_hdridx_flds():
            fld2col_widths[fld] = 2
        return fld2col_widths

    def _get_prtfmt(self, key="fmta"):
        """Return print format for Grouper, which includes hdr1usr01 and num_usrgos."""
        prtfmt = self.sortobj.grprobj.gosubdag.prt_attr[key]
        prtfmt = prtfmt.replace("{NS}", "{NS} {num_usrgos:>4} uGOs")
        return "".join(['{hdr1usr01:2}', prtfmt, '\n'])


# Copyright (C) 2016-2018, DV Klopfenstein, H Tang, All rights reserved.
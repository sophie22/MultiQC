#!/usr/bin/env python

""" MultiQC submodule to parse output from RSeQC junction_annotation.py
http://rseqc.sourceforge.net/#junction-annotation-py """

from collections import OrderedDict
import logging
import re

from multiqc import config

# Initialise the logger
log = logging.getLogger(__name__)


def parse_reports(self):
    """ Find RSeQC junction_annotation reports and parse their data """
    
    # Set up vars
    self.junction_annotation_data = dict()
    regexes = {
        'total_splicing_events': r"^Total splicing  Events:\s*(\d+)$",
        'known_splicing_events': r"^Known Splicing Events:\s*(\d+)$",
        'partial_novel_splicing_events': r"^Partial Novel Splicing Events:\s*(\d+)$",
        'novel_splicing_events': r"^Novel Splicing Events:\s*(\d+)$",
        'total_splicing_junctions': r"^Total splicing  Junctions:\s*(\d+)$",
        'known_splicing_junctions': r"^Known Splicing Junctions:\s*(\d+)$",
        'partial_novel_splicing_junctions': r"^Partial Novel Splicing Junctions:\s*(\d+)$",
        'novel_splicing_junctions': r"^Novel Splicing Junctions:\s*(\d+)$",
    }
    
    # Go through files and parse data using regexes
    for f in self.find_log_files(config.sp['rseqc']['junction_annotation']):
        d = dict()
        for k, r in regexes.items():
            r_search = re.search(r, f['f'], re.MULTILINE)
            if r_search:
                d[k] = int(r_search.group(1))
        
        # Calculate some percentages
        if 'total_splicing_events' in d:
            t = float(d['total_splicing_events'])
            if 'known_splicing_events' in d:
                d['known_splicing_events_pct'] = (float(d['known_splicing_events']) / t)*100.0
            if 'partial_novel_splicing_events' in d:
                d['partial_novel_splicing_events_pct'] = (float(d['partial_novel_splicing_events']) / t)*100.0
            if 'novel_splicing_events' in d:
                d['novel_splicing_events_pct'] = (float(d['novel_splicing_events']) / t)*100.0
        if 'total_splicing_junctions' in d:
            t = float(d['total_splicing_junctions'])
            if 'known_splicing_junctions' in d:
                d['known_splicing_junctions_pct'] = (float(d['known_splicing_junctions']) / t)*100.0
            if 'partial_novel_splicing_junctions' in d:
                d['partial_novel_splicing_junctions_pct'] = (float(d['partial_novel_splicing_junctions']) / t)*100.0
            if 'novel_splicing_junctions' in d:
                d['novel_splicing_junctions_pct'] = (float(d['novel_splicing_junctions']) / t)*100.0
        
        if len(d) > 0:
            self.junction_annotation_data[f['s_name']] = d
    
    if len(self.junction_annotation_data) > 0:
        
        # Log output
        self.sample_count += len(self.junction_annotation_data)
        log.info("Found {} junction_annotation reports".format(len(self.junction_annotation_data)))
    
        # Write to file
        self.write_data_file(self.junction_annotation_data, 'multiqc_rseqc_junction_annotation')
        
        # Plot junction annotations
        keys = OrderedDict()
        keys['known_splicing_junctions'] = { 'name': 'Known Splicing Junctions' }
        keys['partial_novel_splicing_junctions'] = { 'name': 'Partial Novel Splicing Junctions' }
        keys['novel_splicing_junctions'] = { 'name': 'Novel Splicing Junctions' }
        pconfig = {
            'id': 'rseqc_junction_annotation_junctions_plot',
            'title': 'STAR: Splicing Junctions',
            'ylab': '# Junctions',
            'cpswitch_counts_label': 'Number of Junctions'
        }
        junc_plot = self.plot_bargraph(self.junction_annotation_data, keys, pconfig)
        
        # Plot event annotations
        keys = OrderedDict()
        keys['known_splicing_events'] = { 'name': 'Known Splicing Events' }
        keys['partial_novel_splicing_events'] = { 'name': 'Partial Novel Splicing Events' }
        keys['novel_splicing_events'] = { 'name': 'Novel Splicing Events' }
        pconfig = {
            'id': 'rseqc_junction_annotation_events_plot',
            'title': 'STAR: Splicing Events',
            'ylab': '# Events',
            'cpswitch_counts_label': 'Number of Events'
        }
        event_plot = self.plot_bargraph(self.junction_annotation_data, keys, pconfig)
        
        # Write section
        self.sections.append({
            'name': 'Junction Annotation',
            'anchor': 'rseqc_junction_annotation',
            'content': "<p>This program compares detected splice junctions to" \
                " a reference gene model. An RNA read can be spliced 2" \
                " or more times, each time is called a splicing event.</p>" +
                event_plot + "<hr><p>Multiple splicing events spanning the same" \
                " intron can be consolidated into one splicing junction.</p>" +
                junc_plot
        })
    
    
        
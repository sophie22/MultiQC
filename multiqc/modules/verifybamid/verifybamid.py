#!/usr/bin/env python

""" MultiQC module to parse output from VerifyBAMID """

from __future__ import print_function
from collections import OrderedDict
import logging
from multiqc import config
from multiqc.plots import table
from multiqc.modules.base_module import BaseMultiqcModule

# Initialise the logger
log = logging.getLogger(__name__)

class MultiqcModule(BaseMultiqcModule):
	"""
	 module class, parses stderr logs.
	"""

	def __init__(self):
		# Initialise the parent object
		super(MultiqcModule, self).__init__(name='verifyBAMID', anchor='verifybamid',
		href='https://genome.sph.umich.edu/wiki/VerifyBamID',
		info="detect sample contamination and/or sample swap")
		
		# flag to hide columns if no chip data
		self.hide_chip_columns=True

		# default values for columns
		self.defaults = {
			'max': 100,
			'min': 0,
			'suffix': '%',
			'format': '{:,.3f}',
			'modify': lambda x:x * 100.0 if x != "NA" else x,
			'scale': 'OrRd',
			}


		# dictionary to hold all data for each sample
		self.verifybamid_data = dict()

		# for each file ending in self.SM
		for f in self.find_log_files('verifybamid/selfsm'):
			# pass the file to function self.parse_selfsm to parse file
			parsed_data = self.parse_selfsm(f)
			# if a result was returned
			if parsed_data is not None:
				# for each sample extracted from the file
				for s_name in parsed_data:
					# if there are duplicate sample names
					if s_name in self.verifybamid_data:
						# write this to log
						log.debug("Duplicate sample name found! Overwriting: {}".format(s_name))
					# add the sample as a key to the verifybamid_data dictionary and the dictionary of values as the value
					self.verifybamid_data[s_name] = parsed_data[s_name]
				# add data source to multiqc_sources.txt 
				self.add_data_source(f)
		
		# Filter to strip out ignored sample names as per config.yaml
		self.verifybamid_data = self.ignore_samples(self.verifybamid_data)

		if len(self.verifybamid_data) == 0:
			raise UserWarning

		# print number of verifyBAMID reports found and parsed
		log.info("Found {} reports".format(len(self.verifybamid_data)))

		# Write parsed report data to a file	
		self.write_data_file(self.verifybamid_data, 'multiqc_verifybamid')

		# add to General Stats Table
		self.verifybamid_general_stats_table()

		# add section with the values from the verify BAM ID output
		self.verifybamid_table()


	def parse_selfsm(self, f):
		""" Go through selfSM file and create a dictionary with the sample name as a key, """
		#create a dictionary to populate from this sample's file
		parsed_data = dict()
		# set a empty variable which denotes if the headers have been read
		headers = None
		# for each line in the file
		for l in f['f'].splitlines():
			# split the line on tab
			s = l.split("\t")
			# if we haven't already read the header line
			if headers is None:
				# assign this list to headers variable
				headers = s
			# for all rows after the first
			else:
				# clean the sample name (first column) and assign to s_name
				s_name = self.clean_s_name(s[0], f['root'])
				# create a dictionary entry with the first column as a key (sample name) and empty dictionary as a value
				parsed_data[s_name] = {}
				# for each item in list of items in the row
				for i, v in enumerate(s):
					# if it's not the first element (if it's not the name)
					if i != 0:
						# see if CHIP is in the column header and the value is not NA
						if "CHIP" in [headers[i]] and v != "NA":
							# set hide_chip_columns = False so they are not hidden
							self.hide_chip_columns=False
						# try and convert the value into a float
						try:
							# and add to the dictionary the key as the corrsponding item from the header and the value from the list
							parsed_data[s_name][headers[i]] = float(v)
						#if can't convert to float...
						except ValueError:
							# add to the dictionary the key as the corrsponding item from the header and the value from the list
							parsed_data[s_name][headers[i]] = v

		# else return the dictionary
		return parsed_data

	def verifybamid_general_stats_table(self):
		""" Take the percentage of contamination from all the parsed *.SELFSM files and add it to the basic stats table at the top of the report """

		# create a dictionary to hold the columns to add to the general stats table
		headers = OrderedDict()
		# available columns are:
		#SEQ_ID RG  CHIP_ID #SNPS   #READS  AVG_DP  FREEMIX FREELK1 FREELK0 FREE_RH FREE_RA CHIPMIX CHIPLK1 CHIPLK0 CHIP_RH CHIP_RA DPREF   RDPHET  RDPALT
		#see https://genome.sph.umich.edu/wiki/VerifyBamID#Interpreting_output_files

		# add the CHIPMIX column. set the title and description
		headers['CHIPMIX'] = dict(self.defaults, **{
			'title': 'Contamination (S+A)',
			'description': 'VerifyBamID: CHIPMIX -   Sequence+array estimate of contamination (NA if the external genotype is unavailable) (0-1 scale)',
			'hidden': self.hide_chip_columns
			})

		# add the FREEMIX column. set the title and description
		headers['FREEMIX'] = dict(self.defaults, **{
			'title': 'Contamination (S)',
			'description': 'VerifyBamID: FREEMIX -   Sequence-only estimate of contamination (0-1 scale).',
			})
		
		# pass the data dictionary and header dictionary to function to add to table.
		self.general_stats_addcols(self.verifybamid_data, headers)

		
	def verifybamid_table(self):
		"""
		Create a table with all the columns from verify BAM ID
		"""
		
		# create an ordered dictionary to preserve the order of columns
		headers = OrderedDict()
		# add each column and the title and description (taken from verifyBAMID website)
		headers['RG']={
			'title': 'Read Group',
			'description': 'ReadGroup ID of sequenced lane.',
			'hidden': all( [ s['RG'] == 'ALL' for s in self.verifybamid_data.values() ] )
		}
		headers['CHIP_ID'] = {
			'title': 'Chip ID',
			'description': 'ReadGroup ID of sequenced lane.',
			'hidden': self.hide_chip_columns,
		}
		headers['#SNPS']= {
			'title': 'SNPS',
			'description': '# SNPs passing the criteria from the VCF file',
			'format': '{:,.0f}',
		}
		headers['#READS']= {
			'title': ' M Reads',
			'description': 'Million reads loaded from the BAM file',
			'format': '{:,.1f}',
			'modify': lambda x:x * 0.000001 if x != "NA" else x,
			'shared_key': 'read_count_multiplier',
		}
		headers['AVG_DP']= {
			'title': 'Average Depth',
			'description': 'Average sequencing depth at the sites in the VCF file',
		}
		# use default columns
		headers['FREEMIX'] = dict(self.defaults, **{
			'title': 'Contamination (Seq)',
			'description': 'VerifyBamID: FREEMIX -   Sequence-only estimate of contamination (0-1 scale).',
		})
		headers['FREELK1']= {
			'title': 'FREEELK1',
			'format': '{:,.0f}',
			'description': 'Maximum log-likelihood of the sequence reads given estimated contamination under sequence-only method',
		}
		headers['FREELK0']= {
			'title': 'FREELK0',
			'format': '{:,.0f}',
			'description': 'Log-likelihood of the sequence reads given no contamination under sequence-only method',
		}
		headers['FREE_RH']= {
			'title': 'FREE_RH',
			'description': 'Estimated reference bias parameter Pr(refBase|HET) (when --free-refBias or --free-full is used)',
			'hidden': all( [ s['FREE_RH'] == 'NA' for s in self.verifybamid_data.values() ] ),
		}
		headers['FREE_RA']= {
			'title': 'FREE_RA',
			'description': 'Estimated reference bias parameter Pr(refBase|HOMALT) (when --free-refBias or --free-full is used)',
			'hidden': all( [ s['FREE_RA'] == 'NA' for s in self.verifybamid_data.values() ] ),
		}
		# use default columns
		headers['CHIPMIX'] = dict(self.defaults, **{
			'title': 'Contamination S+A',
			'description': 'VerifyBamID: CHIPMIX -   Sequence+array estimate of contamination (NA if the external genotype is unavailable) (0-1 scale)',
			'hidden': self.hide_chip_columns
		})
		headers[ 'CHIPLK1']= {
			'title': 'CHIPLK1',
			'description': 'Maximum log-likelihood of the sequence reads given estimated contamination under sequence+array method (NA if the external genotypes are unavailable)',
			'hidden': self.hide_chip_columns,
		}
		headers['CHIPLK0']= {
			'title': 'CHIPLK0',
			'description': ' Log-likelihood of the sequence reads given no contamination under sequence+array method (NA if the external genotypes are unavailable)',
			'hidden': self.hide_chip_columns,
		}
		headers['CHIP_RH']= {
			'title': 'CHIP_RH',
			'description': 'Estimated reference bias parameter Pr(refBase|HET) (when --chip-refBias or --chip-full is used)',
			'hidden': self.hide_chip_columns,
		}
		headers['CHIP_RA']= {
			'title': 'CHIP_RA',
			'description': 'Estimated reference bias parameter Pr(refBase|HOMALT) (when --chip-refBias or --chip-full is used)',
			'hidden': self.hide_chip_columns,
		}
		headers['DPREF']= {
			'title': 'DPREF',
			'description': 'Depth (Coverage) of HomRef site (based on the genotypes of (SELF_SM/BEST_SM), passing mapQ, baseQual, maxDepth thresholds.',
			'hidden': all( [ s['DPREF'] == 'NA' for s in self.verifybamid_data.values() ] ),
		}
		headers['RDPHET']= {
			'title': 'RDPHET',
			'description': 'DPHET/DPREF, Relative depth to HomRef site at Heterozygous site.',
			'hidden': all( [ s['RDPHET'] == 'NA' for s in self.verifybamid_data.values() ] ),
		}
		headers['RDPALT'] = {
			'title': 'RDPALT',
			'description': 'DPHET/DPREF, Relative depth to HomRef site at HomAlt site.',
			'hidden': all( [ s['RDPALT'] == 'NA' for s in self.verifybamid_data.values() ] ),
		}

		
		# send the plot to add section function with data dict and headers
		self.add_section (
			anchor = 'verifybamid-table',
			plot = table.plot(self.verifybamid_data,headers)
		)


	
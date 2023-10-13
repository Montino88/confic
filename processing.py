class Processing:

    @staticmethod
    def extract_pools_data(section):
        """Extract data for all pools."""
        return section  # As section is already a list of pools data

    @staticmethod
    def extract_data_v3(estats_str, keys_of_interest):
        """Extract data for keys of interest from the estats string."""
        data_dict = {}
        
        for key in keys_of_interest:
            value = estats_str.get(key, None)
            if value:
                if isinstance(value, str) and ' ' in value:
                    value = value.split()
                data_dict[key] = value
            else:
                data_dict[key] = 0  # Setting missing values to 0
                
        return data_dict

    @staticmethod
    def process_content(content):
        # Directly accessing the sections of content as it's now a dictionary
        response_section = content.get('response', {})
        pools_section = content.get('pools', [])
        estats_section = content.get('estats', {})

        estats_keys_of_interest = [
            'GHSspd', 'DHspd', 'GHSmm', 'Temp', 'TMax', 'TAvg', 
            'Fan1', 'Fan2', 'Fan3', 'Fan4', 'FanR', 'Vo', 
            'PS', 'PLL0', 'PLL1', 'PLL2', 'Freq', 'Led',
            'MGHS', 'MTmax', 'Core', 'PING', 'Elapsed', 'BOOTBY', 'HW'
        ]
        estats_data = Processing.extract_data_v3(estats_section, estats_keys_of_interest)

        return {
            'response': response_section,
            'pools': pools_section,
            'estats': estats_data
        }

#---------------------------------------------------------------------------
#  ?                                ABOUT
#  @author         :  
#  @email          :  
#  @repo           :  
#  @createdOn      :  
#  @description    : ID of ZTF filters in alert data from Fink 
#---------------------------------------------------------------------------

def fid_to_filter_ztf(fid: int): 
    """Convert a fid to a filter name
    Args:
        fid (int): ID  of a filter 
    return:
        filter(str): name of the filter
    """ 
    switcher = {1: "ztfg", 2: "ztfr", 3: "ztfi"}
    return switcher.get(fid)

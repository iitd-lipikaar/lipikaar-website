def get_components(adj_list):
    visited = [False for i in range(0, len(adj_list))]

    current_comp = []

    def dfs(current_node):
        if visited[current_node]:
            return
        
        current_comp.append(current_node)
        visited[current_node] = True
        for an in adj_list[current_node]:
            dfs(an)

    comps = []

    for i in range(0, len(adj_list)):
        if not visited[i]:
            current_comp = []
            dfs(i)
            comps.append(current_comp)
    
    return comps

# def process_bboxes(bboxes):
    

class DefaultParsingPostprocessor:
    def __init__(self):
        self.name = "Default Parsing Postprocessor"
        # self.postprocessor_dir = os.path.join(document_parsers_dir, "standard_document_parser")
        print(f"Postprocessor: {self.name} loaded.")

    def process_bboxes(self, image_path, bboxes):
        """
        1) Merge overlapping bboxes
        2) Merge 2 bboxes that have a common y value
        """

        # Merging is done in O(n**2), can be optimized later.

        adj_list = [[] for i in range(0, len(bboxes))]

        # for every 2 bboxes, if they have a common point, connect them
        for i in range(0, len(bboxes)):
            for j in range(i + 1, len(bboxes)):
                # Checking common point
                if bboxes[i]['y_min'] > bboxes[j]['y_max'] or bboxes[j]['y_min'] > bboxes[i]['y_max']:
                    # no common vertical location
                    continue

                # Checking percentage overlap
                bbox_1_height = bboxes[i]['y_max'] - bboxes[i]['y_min']
                bbox_2_height = bboxes[j]['y_max'] - bboxes[j]['y_min']
                threshold_overlap = 0.2 * ((bbox_1_height + bbox_2_height) / 2)
                current_overlap = min(bboxes[i]['y_max'], bboxes[j]['y_max']) - max(bboxes[i]['y_min'], bboxes[j]['y_min'])

                if current_overlap < threshold_overlap:
                    continue
                
                # Checking containment: not doing this for now

                adj_list[i].append(j)

        components = get_components(adj_list)

        new_bboxes = []
        
        for component in components:
            merged_component_bbox = {
                'x_min': 1000000,
                'y_min': 1000000,
                'x_max': 0,
                'y_max': 0,
            }

            for bbox_index in component:
                if bboxes[bbox_index]['x_min'] < merged_component_bbox['x_min']:
                    merged_component_bbox['x_min'] = bboxes[bbox_index]['x_min']
                
                if bboxes[bbox_index]['y_min'] < merged_component_bbox['y_min']:
                    merged_component_bbox['y_min'] = bboxes[bbox_index]['y_min']

                if bboxes[bbox_index]['x_max'] > merged_component_bbox['x_max']:
                    merged_component_bbox['x_max'] = bboxes[bbox_index]['x_max']
                
                if bboxes[bbox_index]['y_max'] > merged_component_bbox['y_max']:
                    merged_component_bbox['y_max'] = bboxes[bbox_index]['y_max']

            new_bboxes.append(merged_component_bbox)

        return new_bboxes


parsing_postprocessors = {
    'default': DefaultParsingPostprocessor()
}

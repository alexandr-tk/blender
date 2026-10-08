/* SPDX-FileCopyrightText: 2007 Blender Authors
 *
 * SPDX-License-Identifier: GPL-2.0-or-later */

/** \file
 * \ingroup nodes
 */

#pragma once

#include "BKE_node.hh"
#include "BLI_set.hh"

namespace blender {

struct bNode;
struct bNodeTree;

bNodeSocket *node_add_socket_from_template(bNodeTree *ntree,
                                           bNode *node,
                                           bke::bNodeSocketTemplate *stemp,
                                           eNodeSocketInOut in_out);

void node_verify_sockets(Main *bmain,
                         bNodeTree *ntree,
                         bNode *node,
                         bool do_id_user,
                         Set<FCurve *> *remapped_fcurves = nullptr);

void register_standard_node_socket_types();

namespace nodes {

/**
 * Change the sockets of the node so that it matches the declaration.
 *
 * \param bmain: Optional, necessary for updating animation data.
 * \param remapped_fcurves: Optional tracking shared by the trees updated in this operation.
 */
void update_node_declaration_and_sockets(bNodeTree &ntree,
                                         bNode &node,
                                         Main *bmain = nullptr,
                                         Set<FCurve *> *remapped_fcurves = nullptr);
bool socket_type_supports_fields(eNodeSocketDatatype socket_type);
bool socket_type_supports_attributes(eNodeSocketDatatype socket_type);
bool socket_type_supports_grids(eNodeSocketDatatype socket_type);

}  // namespace nodes
}  // namespace blender

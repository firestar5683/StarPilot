#pragma once
#include "rednose/helpers/ekf.h"
extern "C" {
void car_update_25(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void car_update_24(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void car_update_30(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void car_update_26(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void car_update_27(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void car_update_29(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void car_update_28(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void car_update_31(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void car_err_fun(double *nom_x, double *delta_x, double *out_1832524583205975398);
void car_inv_err_fun(double *nom_x, double *true_x, double *out_970452396869078486);
void car_H_mod_fun(double *state, double *out_4593964073461568413);
void car_f_fun(double *state, double dt, double *out_231308644161984314);
void car_F_fun(double *state, double dt, double *out_2868289483219690466);
void car_h_25(double *state, double *unused, double *out_7797736608546404621);
void car_H_25(double *state, double *unused, double *out_5931441967274123398);
void car_h_24(double *state, double *unused, double *out_9133422513623254856);
void car_H_24(double *state, double *unused, double *out_9101010594292373758);
void car_h_30(double *state, double *unused, double *out_2885742208342474554);
void car_H_30(double *state, double *unused, double *out_3413109008766874771);
void car_h_26(double *state, double *unused, double *out_4918137225453201081);
void car_H_26(double *state, double *unused, double *out_8773798787561371994);
void car_h_27(double *state, double *unused, double *out_8741246461448067056);
void car_H_27(double *state, double *unused, double *out_5587872320567299682);
void car_h_29(double *state, double *unused, double *out_3097181630963667199);
void car_H_29(double *state, double *unused, double *out_2902877664452482587);
void car_h_28(double *state, double *unused, double *out_6668711560817151875);
void car_H_28(double *state, double *unused, double *out_7985276681522013161);
void car_h_31(double *state, double *unused, double *out_3787573678896021836);
void car_H_31(double *state, double *unused, double *out_8147590685328020518);
void car_predict(double *in_x, double *in_P, double *in_Q, double dt);
void car_set_mass(double x);
void car_set_rotational_inertia(double x);
void car_set_center_to_front(double x);
void car_set_center_to_rear(double x);
void car_set_stiffness_front(double x);
void car_set_stiffness_rear(double x);
}
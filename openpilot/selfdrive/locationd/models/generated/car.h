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
void car_err_fun(double *nom_x, double *delta_x, double *out_3365569118000208058);
void car_inv_err_fun(double *nom_x, double *true_x, double *out_5380110975370610231);
void car_H_mod_fun(double *state, double *out_2504311089359476703);
void car_f_fun(double *state, double dt, double *out_2113948687906359301);
void car_F_fun(double *state, double dt, double *out_206720746751575203);
void car_h_25(double *state, double *unused, double *out_4746524988464866507);
void car_H_25(double *state, double *unused, double *out_9001334049249506654);
void car_h_24(double *state, double *unused, double *out_2794460991545559300);
void car_H_24(double *state, double *unused, double *out_3727839766336494060);
void car_h_30(double *state, double *unused, double *out_2714033775784021818);
void car_H_30(double *state, double *unused, double *out_4917713694332436764);
void car_h_26(double *state, double *unused, double *out_7715707043444867463);
void car_H_26(double *state, double *unused, double *out_5703906705585988738);
void car_h_27(double *state, double *unused, double *out_1509299733494180747);
void car_H_27(double *state, double *unused, double *out_2742950382532011853);
void car_h_29(double *state, double *unused, double *out_2110717891107544301);
void car_H_29(double *state, double *unused, double *out_5427945038646828948);
void car_h_28(double *state, double *unused, double *out_2596026381850645074);
void car_H_28(double *state, double *unused, double *out_345546021577298374);
void car_h_31(double *state, double *unused, double *out_4903711656815995652);
void car_H_31(double *state, double *unused, double *out_5077698603352637262);
void car_predict(double *in_x, double *in_P, double *in_Q, double dt);
void car_set_mass(double x);
void car_set_rotational_inertia(double x);
void car_set_center_to_front(double x);
void car_set_center_to_rear(double x);
void car_set_stiffness_front(double x);
void car_set_stiffness_rear(double x);
}
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
void car_err_fun(double *nom_x, double *delta_x, double *out_1972702472511725479);
void car_inv_err_fun(double *nom_x, double *true_x, double *out_3741555659818717473);
void car_H_mod_fun(double *state, double *out_4845788339544047954);
void car_f_fun(double *state, double dt, double *out_4185306989729419910);
void car_F_fun(double *state, double dt, double *out_8252178874365212967);
void car_h_25(double *state, double *unused, double *out_4739826667919645243);
void car_H_25(double *state, double *unused, double *out_2698629402266667542);
void car_h_24(double *state, double *unused, double *out_6091047700113278923);
void car_H_24(double *state, double *unused, double *out_2121692102389320721);
void car_h_30(double *state, double *unused, double *out_7687552658275130204);
void car_H_30(double *state, double *unused, double *out_2569290455123427472);
void car_h_26(double *state, double *unused, double *out_7946639312164568029);
void car_H_26(double *state, double *unused, double *out_1042873916607388682);
void car_h_27(double *state, double *unused, double *out_3665830151724581410);
void car_H_27(double *state, double *unused, double *out_394527143323002561);
void car_h_29(double *state, double *unused, double *out_8290868542951607721);
void car_H_29(double *state, double *unused, double *out_3079521799437819656);
void car_h_28(double *state, double *unused, double *out_6846547824895893173);
void car_H_28(double *state, double *unused, double *out_2002877217631710918);
void car_h_31(double *state, double *unused, double *out_3141445982834403942);
void car_H_31(double *state, double *unused, double *out_2729275364143627970);
void car_predict(double *in_x, double *in_P, double *in_Q, double dt);
void car_set_mass(double x);
void car_set_rotational_inertia(double x);
void car_set_center_to_front(double x);
void car_set_center_to_rear(double x);
void car_set_stiffness_front(double x);
void car_set_stiffness_rear(double x);
}
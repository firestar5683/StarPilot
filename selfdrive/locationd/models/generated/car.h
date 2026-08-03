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
void car_err_fun(double *nom_x, double *delta_x, double *out_2633561206191248032);
void car_inv_err_fun(double *nom_x, double *true_x, double *out_5222322722539771080);
void car_H_mod_fun(double *state, double *out_4733519652188373948);
void car_f_fun(double *state, double dt, double *out_9187320060872601910);
void car_F_fun(double *state, double dt, double *out_3219504763184105906);
void car_h_25(double *state, double *unused, double *out_1821652184812404746);
void car_H_25(double *state, double *unused, double *out_4337363035662665471);
void car_h_24(double *state, double *unused, double *out_258826568498121593);
void car_H_24(double *state, double *unused, double *out_9206177900690372323);
void car_h_30(double *state, double *unused, double *out_1546458122527898857);
void car_H_30(double *state, double *unused, double *out_8865059365790273669);
void car_h_26(double *state, double *unused, double *out_4254367670776586025);
void car_H_26(double *state, double *unused, double *out_8078866354536721695);
void car_h_27(double *state, double *unused, double *out_7579637098806142702);
void car_H_27(double *state, double *unused, double *out_7406921396118853036);
void car_h_29(double *state, double *unused, double *out_8981601556956599670);
void car_H_29(double *state, double *unused, double *out_8354828021475881485);
void car_h_28(double *state, double *unused, double *out_4659949187422787859);
void car_H_28(double *state, double *unused, double *out_5009517035164139557);
void car_h_31(double *state, double *unused, double *out_7316065099871446436);
void car_H_31(double *state, double *unused, double *out_8705074456770073171);
void car_predict(double *in_x, double *in_P, double *in_Q, double dt);
void car_set_mass(double x);
void car_set_rotational_inertia(double x);
void car_set_center_to_front(double x);
void car_set_center_to_rear(double x);
void car_set_stiffness_front(double x);
void car_set_stiffness_rear(double x);
}